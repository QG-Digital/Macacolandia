# Correção do publicador

- [ ] Parar de copiar o projeto-fonte inteiro para o repositório.
- [ ] Criar diretório temporário público contendo somente site e artefatos finais.
- [ ] Compilar o executável antes da publicação.
- [ ] Publicar instalador/executável e landing page, sem backend, fonte ou scripts internos.
- [ ] Limpar arquivos antigos do repositório remoto na próxima publicação.
- [ ] Validar o conteúdo do commit antes do push.

# Ajuste de identidade visual da landing

- [ ] Remover azul e laranja institucionais da landing page do Macacolandia.
- [ ] Aplicar a paleta do app: verde escuro, creme, amarelo, coral e azul-grafite.
- [ ] Ajustar estados de hover, botões, cards, fundo e rodapé para a mesma identidade.
- [ ] Verificar contraste e responsividade.
- [ ] Gerar novo ZIP com site e assets atualizados.

# Correção de build e release

- [ ] Confirmar onde o compilador grava o executável.
- [ ] Garantir que o publicador detecte o artefato real do build.
- [ ] Criar a release do GitHub e anexar instalador/executável.
- [ ] Não publicar código-fonte nem arquivos internos na release/site.
- [ ] Validar o fluxo com simulação antes do envio real.

# Localização do NSIS

- [ ] Procurar `makensis.exe` no PATH, locais comuns e todos os volumes Windows.
- [ ] Mostrar no console qual caminho do NSIS foi encontrado.
- [ ] Exigir `Macacolandia-Setup.exe` antes de criar a release.
- [ ] Testar a descoberta sem executar uma publicação real.
