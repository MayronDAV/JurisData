# Guia de Contribuição

Obrigado pelo seu interesse em contribuir com JurisData! 💡
Contribuições são muito bem-vindas, seja para:

- Reportar um bug 🐞
- Enviar uma correção 🔧
- Sugerir novas funcionalidades ✨
- Melhorar a documentação ou qualidade do código 📚

## Como Contribuir

1. Faça um fork do repositório.
2. Crie uma branch para sua contribuição.
3. Certifique-se de que seu código está funcionando corretamente (build + testes).
4. Abra um Pull Request descrevendo claramente suas mudanças.

## Reportando Bugs

- Abra uma issue no nosso GitHub Issue Tracker
- Use o template de [bug report][bug-report].
- Inclua o máximo de detalhes possível: como reproduzir, comportamento esperado e logs (se houver).

## Solicitando Novas Funcionalidades

- Abra uma issue no nosso
- Use o template de [feature request][feature-request].
- Explique:
  - Qual problema você deseja resolver.
  - Como você tentou resolver com os recursos atuais.
  - Como a nova funcionalidade ajudaria.
- Se possível, adicione exemplos (como snippets de código).

## Licença

Todas as contribuições serão feitas sob a licença [Apache-2.0 License](https://github.com/MayronDAV/JurisData/blob/master/LICENSE). Ao enviar código, você concorda que sua contribuição será licenciada sob os mesmos termos do projeto.

## Convenções de Código

- C/C++:
  - Nomes de arquivos: `UpperCamelCase`
  - Classes: `UpperCamelCase`
  - Variáveis: `lowerCamelCase`
  - Variáveis públicas (membro): `UpperCamelCase`
  - Variáveis privadas (membro): `m_UpperCamelCase`
  - Variáveis estáticas públicas: `UpperCamelCase`
  - Variáveis estáticas privadas: `s_UpperCamelCase`
  - Argumentos de funções: `p_UpperCamelCase`
  - Nomes de métodos/funções: `UpperCamelCase`
  - Variáveis ​​de membro de classe devem ser declaradas no final do arquivo, separadas das declarações de função.
  - Macros: **`SNAKE_CASE`**.
- Python:
  - Nomes de arquivos: `UpperCamelCase`
  - Classes: `UpperCamelCase`
  - Variáveis: `lowerCamelCase`
  - Variáveis públicas (membro): `UpperCamelCase`
  - Variáveis privadas (membro): `m_UpperCamelCase`
  - Argumentos de funções: `p_UpperCamelCase`
  - Nomes de métodos/funções: `UpperCamelCase`
  - Variáveis ​​de membro de classe devem ser declaradas no inicio da classe.

[bug-report]: https://github.com/MayronDAV/JurisData/blob/master/.github/ISSUE_TEMPLATE/bug_report.md
[feature-request]: https://github.com/MayronDAV/JurisData/blob/master/.github/ISSUE_TEMPLATE/feature_request.md