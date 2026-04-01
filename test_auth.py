#!/usr/bin/env python3
"""Testes funcionais do sistema de login."""
import requests

print("=" * 70)
print("TESTES DE AUTENTICAÇÃO - FLASK LOGIN")
print("=" * 70)

# Teste 1: GET / sem sessão - deve redirecionar para /login
print('\n[TESTE 1] GET / sem sessão')
r = requests.get('http://localhost:5000/', allow_redirects=False)
print(f'  Status: {r.status_code} (esperado: 302)')
print(f'  Location: {r.headers.get("Location", "N/A")} (esperado: /login)')
test1_pass = r.status_code == 302 and r.headers.get("Location") == "/login"
print(f'  [PASSOU]' if test1_pass else f'  [FALHOU]')

# Teste 2: GET /login - deve renderizar página de login
print('\n[TESTE 2] GET /login - renderiza página')
r = requests.get('http://localhost:5000/login')
print(f'  Status: {r.status_code} (esperado: 200)')
print(f'  Contém form: {"[OK]" if "<form" in r.text else "[NOK]"} (esperado: [OK])')
print(f'  Contém título: {"[OK]" if "Acesso ao Dashboard" in r.text else "[NOK]"} (esperado: [OK])')
test2_pass = r.status_code == 200 and "<form" in r.text and "Acesso ao Dashboard" in r.text
print(f'  [PASSOU]' if test2_pass else f'  [FALHOU]')

# Teste 3: POST /login com credenciais inválidas
print('\n[TESTE 3] POST /login com credenciais inválidas')
r = requests.post('http://localhost:5000/login', data={'usuario': 'invalido', 'senha': 'errada'})
print(f'  Status: {r.status_code} (esperado: 200)')
print(f'  Mensagem de erro: {"[OK]" if "Usuário ou senha inválidos" in r.text else "[NOK]"} (esperado: [OK])')
print(f'  Form ainda presente: {"[OK]" if "<form" in r.text else "[NOK]"} (esperado: [OK])')
test3_pass = r.status_code == 200 and "Usuário ou senha inválidos" in r.text
print(f'  [PASSOU]' if test3_pass else f'  [FALHOU]')

# Teste 4: POST /login com credenciais válidas
print('\n[TESTE 4] POST /login com credenciais válidas (admin/admin123)')
s = requests.Session()
r = s.post('http://localhost:5000/login', data={'usuario': 'admin', 'senha': 'admin123'}, allow_redirects=False)
print(f'  Status: {r.status_code} (esperado: 302)')
print(f'  Location: {r.headers.get("Location", "N/A")} (esperado: /)')
print(f'  Sessão criada: {"[OK]" if len(s.cookies) > 0 else "[NOK]"} (esperado: [OK])')
test4_pass = r.status_code == 302 and r.headers.get("Location") == "/"
print(f'  [PASSOU]' if test4_pass else f'  [FALHOU]')

# Teste 5: Acessar / com sessão válida
print('\n[TESTE 5] GET / com sessão válida')
r = s.get('http://localhost:5000/', allow_redirects=False)
print(f'  Status: {r.status_code} (esperado: 200)')
print(f'  Dashboard renderizado: {"[OK]" if "Dashboard — Erros de Pedido" in r.text else "[NOK]"} (esperado: [OK])')
test5_pass = r.status_code == 200 and "Dashboard — Erros de Pedido" in r.text
print(f'  [PASSOU]' if test5_pass else f'  [FALHOU]')

# Teste 6: POST /logout
print('\n[TESTE 6] POST /logout')
r = s.get('http://localhost:5000/logout', allow_redirects=False)
print(f'  Status: {r.status_code} (esperado: 302)')
print(f'  Location: {r.headers.get("Location", "N/A")} (esperado: /login)')
test6_pass = r.status_code == 302 and r.headers.get("Location") == "/login"
print(f'  [PASSOU]' if test6_pass else f'  [FALHOU]')

# Teste 7: Verificar que sessão foi limpa após logout
print('\n[TESTE 7] GET / após logout (sessão deve estar limpa)')
r = s.get('http://localhost:5000/', allow_redirects=False)
print(f'  Status: {r.status_code} (esperado: 302)')
print(f'  Location: {r.headers.get("Location", "N/A")} (esperado: /login)')
test7_pass = r.status_code == 302 and r.headers.get("Location") == "/login"
print(f'  [PASSOU]' if test7_pass else f'  [FALHOU]')

# Resumo
print("\n" + "=" * 70)
tests_passed = sum([test1_pass, test2_pass, test3_pass, test4_pass, test5_pass, test6_pass, test7_pass])
print(f"RESULTADO: {tests_passed}/7 testes passaram.")
if tests_passed == 7:
    print("[OK] IMPLEMENTAÇÃO DE LOGIN FUNCIONA CORRETAMENTE!")
else:
    print(f"[NOK] {7 - tests_passed} teste(s) falharam.")
print("=" * 70)
