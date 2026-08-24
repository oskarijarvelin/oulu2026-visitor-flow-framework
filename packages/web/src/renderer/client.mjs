/**
 * Selainpuolen hydraatio vanilla-saarekkeille. Astro kutsuu tata kun `client:visible`
 * laukeaa, ja antaa saarekkeen juurielementin seka build-aikana sarjallistetut propsit.
 */

export default (element) =>
  (Component, props) => {
    element.replaceChildren();
    Component(element, props);
  };
