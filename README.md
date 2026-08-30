# Macacolandia

Macacolandia é um explorador visual local de arquivos feito com Python e pywebview. Ele apresenta pastas e arquivos em visão Tree ou Cubos, permite seleção individual e por intervalo, criação e exclusão de pastas, arrastar e soltar para mover itens, miniaturas de imagens e leitura de arquivos de texto e código.

## Estrutura

`backend.py`, `index.html`, `desktop.css` e `desktop.js` formam o aplicativo desktop. `site/` é a landing page independente, feita somente com `index.html`, `style.css` e `script.js`, com foco em download. `compilador.py` gera o executável. `installer.nsi` prepara o instalador NSIS quando o NSIS estiver instalado. `publicar_macacolandia.py` compila, prepara o instalador quando possível e publica todo o conteúdo no repositório `QG-Digital/Macacolandia`.

## Como executar

Crie um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Depois inicie o aplicativo:

```bash
.venv/bin/python backend.py
```

O app analisa apenas os caminhos escolhidos pelo usuário e não envia arquivos para um serviço remoto.

## Controles

A lista aceita seleção individual por checkbox e seleção de intervalo usando **Shift**. Um clique normal em uma pasta já a seleciona; o indicador à esquerda serve para expandir ou recolher o conteúdo. A visão pode ser alternada entre **Tree** e **Cubos**. Arquivos de texto e código, como JSON, JSON5, JS, HTML, CSS, TOML, YAML, Properties e Python, abrem no leitor interno.

## Landing page

Abra `site/index.html` no navegador ou publique o conteúdo da pasta `site/` em qualquer hospedagem estática. A página é deliberadamente simples e tem botão para a página de releases do repositório oficial. Ela não depende de TypeScript, React ou build.

## Compilar o executável

Instale o PyInstaller e execute:

```bash
python -m pip install pyinstaller
python compilador.py
```

O executável será criado em `dist/Macacolandia`. Para preparar o instalador NSIS no Windows, instale NSIS e execute `makensis installer.nsi`.

## Publicar no GitHub

Autentique o GitHub CLI com `gh auth login` e execute:

```bash
python publicar_macacolandia.py
```

O destino padrão é `QG-Digital/Macacolandia`. Para publicar sem recompilar, use `python publicar_macacolandia.py --skip-build`. Também é possível informar outro destino com `--repo ORGANIZACAO/REPOSITORIO`.
