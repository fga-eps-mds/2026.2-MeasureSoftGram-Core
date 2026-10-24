# Fixtures da comparação US130

`before.json` e `after.json` são **inteiramente sintéticas**, no formato de árvore
SonarQube já usado em `../fga-eps-mds-2021-2-MeasureSoftGram-CLI-04-13-2022-02-13-37-v1.1.1.json`
(Core `2f56e779f01c486503ebd817c89ca0353a8ab3d5`). Nenhuma representa release real.

Cobrem redução (6 → 4), igualdade, zero legítimo, inclusão, remoção, métrica
omitida e valor explicitamente `null`. `DIR`, `UTS` e o agregado `TRK` têm
valores sentinela 999 para expor mistura indevida de granularidades.

A fixture histórica permanece intacta e será usada diretamente nos testes para
validar o formato original, com valores e caminhos que já estavam no repositório.
Não há par histórico do mesmo projeto que comprove uma evolução real entre releases.
