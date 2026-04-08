# Design System Progress

## Status

O catalogo `/design-system` esta estabilizado como ferramenta interna de
referencia para a V2 web. Ele documenta tokens, primitives e recipes usados nas
rotas de produto, sem entrar na navegacao principal.

## Correcoes aplicadas neste ciclo

- Metadata dedicada para `/design-system`
- Limpeza de encoding em catalogo, layout e componentes compartilhados
- Remocao de aliases invalidos em `app/globals.css`
- Consolidacao dos recipes compartilhados em `components/shared/design-system-recipes.tsx`
- Adocao visual nas rotas `/`, `/empresas` e `/empresas/[cd_cvm]`
- Padronizacao dos estados de loading, error e not-found

## Recipes aprovados

- `PageShell`
- `SurfaceCard`
- `InfoChip`
- `SectionHeading`

Esses recipes sustentam as superficies de produto atuais e devem ser
preferidos antes de criar novas combinacoes de `bg`, `border`, `shadow`,
`radius` ou spacing diretamente na pagina.

## Checklist por superficie

### Base

- [x] Tokens oficiais em `app/globals.css`
- [x] Metadata especifica para `/design-system`
- [x] Catalogo com copy limpa e papel interno explicito
- [x] Footer com link secundario para o Design System
- [x] Header sem destaque excessivo para areas ainda indisponiveis

### Produto

- [x] Home alinhada ao sistema
- [x] Diretorio `/empresas` alinhado ao sistema
- [x] Detalhe `/empresas/[cd_cvm]` alinhado ao sistema
- [x] Error boundary, loading e not-found alinhados ao sistema

### Verificacao

- [x] `npm run lint`
- [x] `npm run typecheck`
- [x] `npm run build`
- [x] `npm run test:unit`
- [x] `npm run test:e2e`
- [x] Revisao visual final com Playwright

Observacao:

- `npm run lint` ainda emite warnings nao bloqueantes em componentes de showcase
  antigos, sem impacto no slice de produto atual.

## Pendencias fora de escopo

- Auditoria completa de dark mode nas superficies de produto
- Expansao do sistema para rotas ainda nao publicadas
- Introducao de novos primitives antes de necessidade real
- Refatoracoes estruturais da API ou do backend Python
