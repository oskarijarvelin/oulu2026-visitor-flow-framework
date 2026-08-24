/**
 * Palvelinpuolen renderoija vanilla-saarekkeille.
 *
 * Saarekkeet piirtavat SVG:n Observable Plotilla, mika vaatii DOMin, joten palvelimella
 * ne eivat piirra kaaviota. Sen sijaan ne jattavat paikanvaraajan kahdesta syysta:
 *
 * 1. `client:visible` tarkkailee saarekkeen lapsielementteja. Ilman lasta
 *    IntersectionObserver ei saa mitaan tarkkailtavaa eika saareke hydratoidu koskaan.
 * 2. Paikanvaraaja varaa kaaviolle korkeuden, joten sivu ei hyppaa kun kaavio ilmestyy.
 *
 * Sivun tekstisisalto ja kaavioiden tekstivastineet tulevat .astro-komponenteista,
 * joten sivu on ymmarrettava myos ilman JavaScriptia.
 */

const DEFAULT_HEIGHT = 260;

function check(Component) {
  return typeof Component === 'function' && Component.isVanillaIsland === true;
}

function renderToStaticMarkup(_Component, props) {
  const height = Number(props?.placeholderHeight ?? DEFAULT_HEIGHT);
  const label = String(props?.ariaLabel ?? 'Kaavio');
  return {
    html:
      `<div class="chart-placeholder" aria-hidden="true" style="min-height:${height}px">` +
      `<span class="sr-only">${escapeHtml(label)}</span>` +
      '</div>',
  };
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export default { name: 'vanilla', check, renderToStaticMarkup };
