# Radar do Diário de Itupeva

Lê o Google Notícias a cada 15 minutos (6h às 23h45, horário de Brasília), monta a lista das notícias relevantes das últimas 24h em `pautas.md` e `pautas.json`, priorizando Itupeva e os assuntos da grade do Diário, e destaca as urgentes.

Quando aparece uma urgente nova, o radar abre uma issue "URGENTE" neste repositório. A issue aciona automaticamente a tarefa Urgente do Claude, que confere a notícia, prepara o post e pede aprovação ao editor.
