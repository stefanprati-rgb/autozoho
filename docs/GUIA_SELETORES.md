# 📋 Sistema de Mapeamento de Seletores - Guia Completo

## 🎯 O que é?

Um sistema robusto para gerenciar seletores CSS e XPath de elementos da interface do Zoho, com fallback automático e fácil manutenção.

## 📁 Estrutura de Arquivos

```
AutoZoho/
├── config/
│   ├── zoho_selectors.json          # Seletores da tela WhatsApp
│   └── template_mapeamento.json     # Template para mapear outras telas
├── utils/
│   └── selector_manager.py          # Classe helper para usar os seletores
└── examples/
    └── exemplo_uso_seletores.py     # Exemplos práticos de uso
```

## 🚀 Como Usar

### 1. **Uso Básico**

```python
from utils.selector_manager import get_selector_manager

# Obter instância do gerenciador
sm = get_selector_manager()

# Clicar em um botão
sm.click_element(driver, 'contato', 'edicao', 'botao_editar')

# Obter texto de um elemento
email = sm.get_text(driver, 'contato', 'campos', 'email')

# Enviar texto para um campo
sm.send_keys(driver, '+5511999999999', 'contato', 'campos', 'celular')
```

### 2. **Métodos Disponíveis**

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `find_element_safe()` | Localiza elemento com fallback automático | WebElement ou None |
| `find_elements_safe()` | Localiza múltiplos elementos | List[WebElement] |
| `click_element()` | Localiza e clica no elemento | bool |
| `get_text()` | Obtém texto do elemento | str |
| `send_keys()` | Envia texto para campo | bool |

### 3. **Fallback Automático**

O sistema tenta automaticamente nesta ordem:
1. ✅ CSS Selector
2. ✅ XPath
3. ✅ Seletores alternativos (label_css, input_css, etc)

Se um falhar, tenta o próximo automaticamente!

## 📝 Como Mapear Novas Telas

### Passo 1: Copiar o Template

```bash
cp config/template_mapeamento.json config/nova_tela_selectors.json
```

### Passo 2: Preencher os Dados

```json
{
  "pagina": "Zoho CRM - Página de Contatos",
  "url": "https://crm.zoho.com/contacts",
  "data_mapeamento": "2025-11-28",
  
  "lista_contatos": {
    "tabela": {
      "container": {
        "css": "table.contacts-table",
        "xpath": "//table[contains(@class, 'contacts')]"
      },
      "linhas": {
        "css": "table.contacts-table tbody tr",
        "xpath": "//table//tbody//tr"
      }
    },
    "filtros": {
      "busca": {
        "css": "input[name='search']",
        "xpath": "//input[@name='search']"
      }
    }
  }
}
```

### Passo 3: Usar no Código

```python
# Carregar o novo mapeamento
sm = SelectorManager('config/nova_tela_selectors.json')

# Usar os seletores
sm.click_element(driver, 'lista_contatos', 'filtros', 'busca')
```

## 💡 Exemplos Práticos

### Exemplo 1: Corrigir Telefones (Refatorado)

**ANTES:**
```python
SELETOR_BOTAO_EDITAR = 'button[data-id="iconContainer"]'
btn = driver.find_element(By.CSS_SELECTOR, SELETOR_BOTAO_EDITAR)
btn.click()
```

**DEPOIS:**
```python
sm = get_selector_manager()
sm.click_element(driver, 'contato', 'edicao', 'botao_editar')
```

### Exemplo 2: Extrair Informações

```python
def obter_dados_contato(driver):
    sm = get_selector_manager()
    
    return {
        'email': sm.get_text(driver, 'contato', 'campos', 'email'),
        'celular': sm.get_text(driver, 'contato', 'campos', 'celular'),
        'telefone': sm.get_text(driver, 'contato', 'campos', 'telefone')
    }
```

### Exemplo 3: Navegação

```python
def navegar_whatsapp(driver):
    sm = get_selector_manager()
    return sm.click_element(driver, 'navegacao', 'superior', 'whatsapp')
```

## 🎨 Boas Práticas

### ✅ DO (Faça)

- Use IDs quando disponíveis (mais estáveis)
- Forneça sempre CSS **E** XPath
- Organize por categorias lógicas
- Use nomes descritivos
- Mantenha `data_mapeamento` atualizada

### ❌ DON'T (Não Faça)

- Seletores muito específicos (ex: `div > div > div > button`)
- Hardcode seletores no código Python
- Esqueça de testar ambos os seletores
- Use apenas um tipo de seletor

## 🔧 Dicas de Mapeamento

### 1. **Encontrar Seletores CSS**

No DevTools do navegador:
1. Inspecione o elemento (F12)
2. Clique com botão direito no HTML
3. Copy → Copy selector

### 2. **Encontrar XPath**

No DevTools:
1. Inspecione o elemento
2. Clique com botão direito no HTML
3. Copy → Copy XPath

### 3. **Testar Seletores**

No Console do navegador:
```javascript
// Testar CSS
document.querySelector('button[data-id="iconContainer"]')

// Testar XPath
$x("//button[@data-id='iconContainer']")
```

## 📊 Vantagens do Sistema

| Antes | Depois |
|-------|--------|
| ❌ Seletores espalhados no código | ✅ Centralizados em JSON |
| ❌ Sem fallback | ✅ Fallback automático CSS→XPath |
| ❌ Difícil manutenção | ✅ Fácil atualização |
| ❌ Sem logs | ✅ Logs automáticos |
| ❌ Código duplicado | ✅ Reutilizável |

## 🚦 Próximos Passos

1. **Mapear outras telas** que você usa:
   - Página de Clientes
   - Página de Tickets
   - Configurações
   - Relatórios

2. **Refatorar código existente** para usar o SelectorManager:
   - `core/processing.py`
   - `core/messaging.py`
   - Outros scripts

3. **Criar testes** para validar seletores:
   - Script que verifica se todos os seletores funcionam
   - Alerta quando algum seletor quebrar

## 📞 Exemplo Completo

Veja `examples/exemplo_uso_seletores.py` para exemplos completos de:
- Correção de telefones
- Extração de dados
- Navegação entre telas
- Envio de mensagens
- E muito mais!

## 🔄 Manutenção

Quando a interface do Zoho mudar:
1. Abra o JSON correspondente
2. Atualize apenas os seletores que mudaram
3. Atualize `data_mapeamento`
4. Teste com o script

**Não precisa alterar o código Python!** 🎉

---

**Criado em:** 2025-11-28  
**Versão:** 1.0  
**Autor:** AutoZoho Team
