import { island } from '../renderer/index.ts';

export default island<{ label: string }>((element, props) => {
  const span = document.createElement('span');
  span.textContent = props.label;
  element.append(span);
});
