# Guia de Migração - Sistema de Seletores

## 📋 Resumo

Este guia explica como migrar do código antigo (seletores hardcoded) para o novo sistema usando `SelectorManager`.

## 🎯 Vantagens da Migração

| Antes | Depois |
|-------|--------|
| ❌ Seletores hardcoded | ✅ Seletores em JSON |
| ❌ Sem fallback | ✅ Fallback automático CSS→XPath |
| ❌ Difícil manutenção | ✅ Fácil atualização |
| ❌ Código duplicado | ✅ Reutilizável |
| ❌ Logs manuais | ✅ Logs automáticos |

## 🔄 Opções de Migração

### Opção 1: Usar Helpers (Recomendado)

**Mais fácil e seguro** - Use `core/processing_helpers.py`:

```python
# ANTES (processing.py)
from core.processing import corrigir_telefones_na_interface

corrigir_telefones_na_interface(driver, correcoes, nome_cliente)

# DEPOIS (usando helpers)
from core.processing_helpers import corrigir_telefones_modal_inline

corrigir_telefones_modal_inline(driver, correcoes, nome_cliente)
```

### Opção 2: Migração Gradual

Manter código antigo e novo lado a lado:

```python
# Em processing.py - adicionar no topo
USE_SELECTOR_MANAGER = True  # Flag para ativar/desativar

if USE_SELECTOR_MANAGER:
    from core.processing_helpers import corrigir_telefones_na_interface_v2 as corrigir_telefones_na_interface
else:
    # Usar função original
    pass
```

### Opção 3: Substituição Completa

Substituir funções antigas completamente (mais arriscado).

## 📝 Exemplos de Migração

### 1. Correção de Telefones

**ANTES:**
```python
# core/processing.py (linhas 28-30)
SELETOR_BOTAO_EDITAR = 'button[data-id="iconContainer"]' 
SELETOR_BOTAO_SALVAR = 'button[data-id="saveButtonId"]'

def corrigir_telefones_na_interface(driver, correcoes, nome_cliente):
    wait = WebDriverWait(driver, 10)
    try:
        btn_editar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_BOTAO_EDITAR)))
        btn_editar.click()
        # ... mais código ...
```

**DEPOIS:**
```python
# core/processing_helpers.py
from utils.selector_manager import SelectorManager

sm = SelectorManager('config/contato_detalhes_selectors.json')

def corrigir_telefones_modal_inline(driver, correcoes, nome_cliente):
    if not sm.click_element(driver, 'edicao', 'botao_editar'):
        return False
    # ... código simplificado ...
```

### 2. Envio de Mensagem WhatsApp

**ANTES:**
```python
# Provavelmente em messaging.py
campo_canal = driver.find_element(By.XPATH, "//input[@type='text']")
campo_canal.send_keys(departamento)
```

**DEPOIS:**
```python
from utils.selector_manager import SelectorManager

sm = SelectorManager('config/modal_whatsapp_selectors.json')
sm.send_keys(driver, departamento, 'modal', 'body', 'canal_whatsapp', 'input')
```

## 🚀 Workflow Recomendado

### Para Correção de Telefones

```python
from core.processing_helpers import processar_contato_completo

# Workflow completo em uma linha!
processar_contato_completo(
    driver,
    contato_id='919191000000734001',
    nome_cliente='Paulo Silva',
    usar_formulario=False  # True = formulário completo, False = modal inline
)
```

### Para Processamento em Massa

```python
from examples.exemplo_lista_contatos import processar_todas_paginas
from core.processing_helpers import processar_contato_completo

def minha_funcao(driver, contato_info):
    processar_contato_completo(
        driver,
        contato_id=contato_info['id'],
        nome_cliente=contato_info['nome']
    )

# Processar TODAS as páginas
processar_todas_paginas(driver, minha_funcao, max_paginas=5)
```

## 🔧 Funções Disponíveis

### core/processing_helpers.py

| Função | Descrição |
|--------|-----------|
| `corrigir_telefones_modal_inline()` | Corrige usando modal inline (rápido) |
| `corrigir_telefones_formulario_completo()` | Corrige usando formulário completo (robusto) |
| `verificar_e_preparar_correcoes()` | Verifica e prepara lista de correções |
| `processar_contato_completo()` | Workflow completo automático |
| `corrigir_telefones_na_interface_v2()` | Drop-in replacement da função original |

## 📊 Comparação de Performance

```python
from core.processing_helpers import comparar_metodos

# Compara modal inline vs formulário completo
comparar_metodos(driver, contato_id, nome_cliente)
```

Resultado típico:
```
📊 Comparação:
   Modal inline: 3.2s - ✅
   Formulário: 5.8s - ✅
```

**Recomendação:** Use modal inline para velocidade, formulário para robustez.

## ⚠️ Pontos de Atenção

1. **Teste antes de migrar completamente**
   - Use helpers em paralelo com código antigo
   - Valide resultados

2. **Mantenha compatibilidade**
   - Não quebre código existente
   - Use flags de feature

3. **Atualize seletores quando necessário**
   - Se Zoho mudar interface, atualize JSON
   - Não precisa mexer no código Python!

## 📚 Recursos

- **Guia completo:** `docs/GUIA_SELETORES.md`
- **Exemplos:** `examples/exemplo_*.py`
- **Helpers:** `core/processing_helpers.py`
- **Seletores:** `config/*_selectors.json`

## 🎯 Próximos Passos

1. ✅ Testar helpers em ambiente de desenvolvimento
2. ✅ Comparar performance (modal vs formulário)
3. ⏸️ Decidir estratégia de migração
4. ⏸️ Implementar gradualmente
5. ⏸️ Remover código antigo (quando estável)

---

**Criado em:** 2025-11-28  
**Versão:** 1.0
