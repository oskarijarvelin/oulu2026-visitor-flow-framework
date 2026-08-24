import type { AstroIntegration } from 'astro';

/**
 * Rekisteroi kevyen renderoijan, jolla `client:visible` toimii ilman React-, Vue- tai
 * Svelte-integraatiota. Saareke on tavallinen funktio, joka piirtaa annettuun
 * elementtiin.
 */
export function vanillaIslands(): AstroIntegration {
  return {
    name: 'ovf:vanilla-islands',
    hooks: {
      'astro:config:setup': ({ addRenderer }) => {
        addRenderer({
          name: 'vanilla',
          clientEntrypoint: '/src/renderer/client.mjs',
          serverEntrypoint: '/src/renderer/server.mjs',
        });
      },
    },
  };
}

/** Saarekkeen propsit sarjallistetaan JSONiksi, joten ne saavat sisaltaa vain dataa. */
export type IslandProps = Record<string, unknown>;

/** Propsit jotka jokainen saareke tuntee renderoijan kautta. */
export interface CommonIslandProps {
  /**
   * Palvelimella piirrettavan paikanvaraajan korkeus pikseleina. Varaa kaaviolle
   * tilan ennen hydraatiota, jotta sivu ei hyppaa.
   */
  placeholderHeight?: number;
}

/**
 * Saarekekomponentti sellaisena kuin Astro sen nakee: funktio joka ottaa propsit.
 *
 * Ajon aikana renderoija kutsuu funktiota muodossa `(element, props)`, katso
 * `client.mjs`. Tyyppi on kirjoitettu Astron JSX-paattelya varten, joka lukee propsit
 * ensimmaisesta parametrista, ja `island()` hoitaa muunnoksen yhdessa paikassa.
 */
export type VanillaIsland<P extends IslandProps> = ((props: P & CommonIslandProps) => unknown) & {
  isVanillaIsland: true;
};

/** Merkitsee funktion saarekkeeksi, jotta palvelinpuolen `check()` tunnistaa sen. */
export function island<P extends IslandProps>(
  render: (element: HTMLElement, props: P) => void,
): VanillaIsland<P> {
  const component = render as unknown as VanillaIsland<P>;
  component.isVanillaIsland = true;
  return component;
}
