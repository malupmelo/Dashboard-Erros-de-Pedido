# ─────────────────────────────────────────────
# importer.py — Importação da planilha Excel
# ─────────────────────────────────────────────

import os
import glob
import pandas as pd
from datetime import datetime
import tempfile
import shutil
import time
from database import salvar_registros
from config import (
    PASTA_DATA,
    ARQUIVO_FLUXO_EMAILS,
    LEITURA_EXCEL_NROWS_MAX,
    SINCRONIZAR_HOMONIMOS_MAIS_NOVOS,
)

COLUNAS = ["NF", "FORNECEDOR", "PEDIDO", "ERRO", "DATA", "COMPRADOR", "ASSUNTO", "REMETENTE"]
COLUNAS_OBRIGATORIAS = {"NF", "FORNECEDOR", "PEDIDO", "ERRO", "DATA", "COMPRADOR", "REMETENTE"}


def _log_metadados_arquivo(caminho_abs: str):
    st = os.stat(caminho_abs)
    modificado_em = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"  arquivo: {os.path.basename(caminho_abs)}")
    print(f"    caminho absoluto: {caminho_abs}")
    print(f"    modificado em: {modificado_em}")
    print(f"    tamanho (bytes): {st.st_size}")


def _aguardar_arquivo_estavel(caminho_abs: str, tentativas: int = 10, intervalo_seg: float = 0.5):
    """Aguarda estabilidade de mtime e tamanho para reduzir leitura de arquivo em sincronização."""
    ultimo = None
    for _ in range(tentativas):
        st = os.stat(caminho_abs)
        atual = (st.st_mtime, st.st_size)
        if atual == ultimo:
            return
        ultimo = atual
        time.sleep(intervalo_seg)


def _ler_excel_onedrive_safe(caminho_abs: str) -> pd.DataFrame:
    """Lê via cópia temporária para evitar lock/sincronização parcial do OneDrive."""
    _aguardar_arquivo_estavel(caminho_abs)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(caminho_abs, tmp_path)
        return pd.read_excel(tmp_path, dtype=str, nrows=LEITURA_EXCEL_NROWS_MAX)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _sincronizar_homonimo_mais_novo(caminho_abs: str) -> str:
    """Sincroniza para data/ quando há arquivo homônimo mais novo fora da pasta do projeto."""
    if not SINCRONIZAR_HOMONIMOS_MAIS_NOVOS:
        return caminho_abs

    raiz_busca = os.path.dirname(os.path.dirname(os.path.dirname(PASTA_DATA)))
    nome = os.path.basename(caminho_abs)
    try:
        st_ref = os.stat(caminho_abs)
    except OSError:
        return caminho_abs

    padrao = os.path.join(raiz_busca, "**", nome)
    candidatos = [os.path.abspath(p) for p in glob.glob(padrao, recursive=True)]
    candidato_mais_novo = None
    st_mais_novo = None
    for cand in candidatos:
        if cand == caminho_abs:
            continue
        try:
            st_cand = os.stat(cand)
        except OSError:
            continue
        if st_cand.st_mtime > st_ref.st_mtime:
            if st_mais_novo is None or st_cand.st_mtime > st_mais_novo.st_mtime:
                candidato_mais_novo = cand
                st_mais_novo = st_cand

    if not candidato_mais_novo:
        return caminho_abs

    data_ref = datetime.fromtimestamp(st_ref.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    data_cand = datetime.fromtimestamp(st_mais_novo.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"    [AVISO] Existe homônimo mais novo fora de data/: {candidato_mais_novo}")
    print(f"    [AVISO] data/={data_ref} | alternativo={data_cand}")

    if SINCRONIZAR_HOMONIMOS_MAIS_NOVOS:
        try:
            shutil.copy2(candidato_mais_novo, caminho_abs)
            print("    [OK] Arquivo de data/ sincronizado com a versão mais nova.")
        except OSError as e:
            print(f"    [AVISO] Não foi possível sincronizar homônimo mais novo: {e}")
            print("    [AVISO] Leitura seguirá usando o arquivo alternativo mais novo nesta execução.")
            return candidato_mais_novo

    return caminho_abs


def _parse_data_segura(valor: str):
    """Converte strings de data para datetime com validação de faixa de ano."""
    s = (valor or "").strip()
    if not s:
        return None

    formatos = [
        "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y",
    ]

    for fmt in formatos:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.year < 2020 or dt.year > datetime.now().year + 1:
                return None
            return dt
        except ValueError:
            continue

    if s.replace(".", "", 1).isdigit():
        try:
            dt = pd.to_datetime(float(s), unit="D", origin="1899-12-30", errors="coerce")
            if pd.notna(dt):
                dt = dt.to_pydatetime()
                if 2020 <= dt.year <= datetime.now().year + 1:
                    return dt
        except Exception:
            pass

    try:
        dt = pd.to_datetime(s, errors="coerce", utc=True)
        if pd.notna(dt):
            dt = dt.tz_localize(None).to_pydatetime()
            if 2020 <= dt.year <= datetime.now().year + 1:
                return dt
    except Exception:
        pass

    return None


def processar_arquivo(caminho: str) -> pd.DataFrame:
    """
    Processa um arquivo Excel e retorna DataFrame validado.
    Não salva no banco - apenas retorna os dados processados.
    """
    caminho_abs = os.path.abspath(caminho)
    if not os.path.exists(caminho_abs):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_abs}")

    # leitura inicial
    print(f"  lendo arquivo {os.path.basename(caminho_abs)}")
    _log_metadados_arquivo(caminho_abs)
    caminho_abs = _sincronizar_homonimo_mais_novo(caminho_abs)
    _log_metadados_arquivo(caminho_abs)
    try:
        df = _ler_excel_onedrive_safe(caminho_abs)
    except PermissionError:
        print(f"    [AVISO] permissao negada ao ler '{caminho_abs}', nova tentativa...")
        time.sleep(1)
        df = _ler_excel_onedrive_safe(caminho_abs)
    print(f"    lidas {len(df)} linhas (antes de normalizar colunas)")
    if len(df) >= LEITURA_EXCEL_NROWS_MAX:
        print(
            "    [AVISO] Limite de leitura atingido "
            f"({LEITURA_EXCEL_NROWS_MAX} linhas). "
            "Aumente LEITURA_EXCEL_NROWS_MAX em config.py se necessário."
        )
    df.columns = [c.strip().upper() for c in df.columns]

    # Mapeamento de colunas alternativas para o padrão do sistema
    MAPA_COLUNAS = {
        "DATARECEBIMENTO": "DATA",
        "TIPOERRO": "ERRO",
    }
    df.rename(columns={k: v for k, v in MAPA_COLUNAS.items() if k in df.columns}, inplace=True)

    colunas_faltando = COLUNAS_OBRIGATORIAS - set(df.columns)
    if colunas_faltando:
        raise ValueError(f"Colunas faltando na planilha '{os.path.basename(caminho)}': {colunas_faltando}")

    # ASSUNTO é opcional — preenche com vazio se não existir
    if "ASSUNTO" not in df.columns:
        df["ASSUNTO"] = ""

    df = df[COLUNAS].dropna(how="all").fillna("")
    after_drop = len(df)
    print(f"    {after_drop} linhas após eliminar linhas vazias")
    datas_convertidas = df["DATA"].apply(_parse_data_segura)
    invalidas = int(datas_convertidas.isna().sum())
    df["DATA"] = datas_convertidas.apply(lambda dt: dt.strftime("%d/%m/%Y") if pd.notna(dt) else "")
    if invalidas > 0:
        print(f"    [AVISO] {invalidas} datas inválidas/fora de faixa foram ignoradas")
    
    # Adiciona coluna com origem do arquivo para referência
    df["_ORIGEM"] = os.path.basename(caminho)

    return df


def importar_pasta_data() -> int:
    """
    Importa TODAS as planilhas .xlsx encontradas em data/.
    Consolida os dados e salva no banco.
    Retorna o total de registros importados.
    """
    if not os.path.isdir(PASTA_DATA):
        raise FileNotFoundError(f"Pasta não encontrada: {PASTA_DATA}")

    # Lista todos os arquivos .xlsx em data/
    arquivos_xlsx = sorted(glob.glob(os.path.join(PASTA_DATA, "*.xlsx")))
    
    if not arquivos_xlsx:
        raise FileNotFoundError(
            f"Nenhuma planilha .xlsx encontrada em data/"
        )

    print(f"\n[IMPORT] Encontradas {len(arquivos_xlsx)} planilha(s) em data/:")
    for arq in arquivos_xlsx:
        print(f"  - {os.path.basename(arq)}")

    # Processa cada planilha e consolida os dados
    todos_registros = []
    arquivos_processados = []
    
    for caminho_arquivo in arquivos_xlsx:
        nome_arquivo = os.path.basename(caminho_arquivo)
        print(f"\n[IMPORT] Processando: {nome_arquivo}")
        
        try:
            df = processar_arquivo(caminho_arquivo)
            registros = df.drop(columns=["_ORIGEM"]).to_dict(orient="records")
            todos_registros.extend(registros)
            arquivos_processados.append(f"{nome_arquivo} ({len(registros)} registros)")
            print(f"[OK] {len(registros)} registros lidos de {nome_arquivo}")
        except Exception as e:
            print(f"[ERRO] Falha ao processar {nome_arquivo}: {e}")
            continue

    if not todos_registros:
        raise ValueError("Nenhum registro válido foi extraído das planilhas")

    # Salva todos os registros consolidados no banco
    salvar_registros(todos_registros, "consolidado_data")

    qtd_total = len(todos_registros)
    print(f"\n[OK] {qtd_total} registros importados no total")
    print("[INFO] Origem consolidada:")
    for orig in arquivos_processados:
        print(f"  - {orig}")
    
    return qtd_total


def importar_excel(caminho: str) -> int:
    """
    Lê a planilha Excel e salva os dados no banco.
    Retorna o número de registros importados.
    Compatibilidade com CLI existente.
    Procura o arquivo na raiz ou na pasta data/.
    """
    # Se arquivo não existe no caminho especificado, tenta em data/
    if not os.path.exists(caminho):
        caminho_data = os.path.join(PASTA_DATA, os.path.basename(caminho))
        if os.path.exists(caminho_data):
            caminho = caminho_data
        else:
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho} ou {caminho_data}")

    df = processar_arquivo(caminho)
    registros = df.drop(columns=["_ORIGEM"]).to_dict(orient="records")
    salvar_registros(registros, os.path.basename(caminho))

    qtd = len(registros)
    print(f"[OK] {qtd} registros importados de '{caminho}'")
    return qtd
