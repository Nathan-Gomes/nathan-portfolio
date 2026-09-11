import { animate, inView, stagger } from 'motion';
import './portfolio-ui.css';
import './portfolio-flow.css';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
function reveal(elements: Element[]) {
  if (!reduced.matches) animate(elements, { opacity: [0, 1], y: [12, 0] }, { duration: 0.3, delay: stagger(0.04) });
}
function button(label: string, text: string) {
  const el = document.createElement('button');
  el.type = 'button';
  el.textContent = text;
  el.setAttribute('aria-label', label);
  el.title = label;
  return el;
}

function enhance(root: HTMLElement) {
  root.classList.add('modern-portfolio');
  root.querySelector('header')!.classList.add('site-navigation');
  root.querySelector('section')!.classList.add('site-introduction');
  const stack = root.querySelector<HTMLElement>('#stack')!;
  root.querySelector('#certifications')!.before(stack);
  const navigation = root.querySelector('header nav')!;
  navigation.querySelector('[href="#certifications"]')!.before(navigation.querySelector('[href="#stack"]')!);
  Object.entries({ projects: 'Selected projects', experience: 'Work experience', stack: 'Technical toolkit', certifications: 'Certifications' }).forEach(([id, title], index) => {
    const section = root.querySelector<HTMLElement>(`#${id}`)!;
    section.classList.add('portfolio-section');
    const heading = section.querySelector('h2')!;
    heading.textContent = title;
    const head = document.createElement('div');
    head.className = 'unified-section-head';
    const number = document.createElement('span');
    number.textContent = String(index + 1).padStart(2, '0');
    number.className = 'section-number';
    head.append(number, heading);
    section.firstElementChild!.replaceWith(head);
  });
  const links = [...navigation.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')];
  let scheduled = false;
  function updateNavigation() {
    const active = links.map(link => root.querySelector<HTMLElement>(link.hash)).filter(section => section && section.getBoundingClientRect().top <= 180).at(-1);
    links.forEach(link => {
      if (active && link.hash === `#${active.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    scheduled = false;
  }
  window.addEventListener('scroll', () => { if (!scheduled) { scheduled = true; requestAnimationFrame(updateNavigation); } }, { passive: true });
  const stackList = stack.querySelector<HTMLElement>('.stack-list')!;
  const panels = [...stackList.querySelectorAll<HTMLElement>('.stack-row')];
  const tablist = document.createElement('div');
  tablist.className = 'toolkit-tabs';
  tablist.setAttribute('role', 'tablist');
  tablist.setAttribute('aria-label', 'Technical skill categories');
  const labels = ['Software', 'Cloud', 'Data', 'Integration', 'Operations'];
  const tabs = panels.map((panel, i) => {
    panel.id = `toolkit-panel-${i}`;
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', `toolkit-tab-${i}`);
    panel.tabIndex = 0;
    const tab = button(labels[i], labels[i]);
    tab.id = `toolkit-tab-${i}`;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', panel.id);
    tab.onclick = () => selectTab(i);
    tablist.append(tab);
    return tab;
  });
  function selectTab(index: number) {
    tabs.forEach((tab, i) => { tab.setAttribute('aria-selected', String(i === index)); tab.tabIndex = i === index ? 0 : -1; panels[i].hidden = i !== index; });
    reveal([panels[index]]);
  }
  tablist.onkeydown = event => {
    const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
    let next: number;
    if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') next = (current + tabs.length - 1) % tabs.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = tabs.length - 1;
    else return;
    event.preventDefault(); selectTab(next); tabs[next].focus();
  };
  stackList.before(tablist);
  selectTab(0);
  const about = [...root.querySelectorAll('section')].find(section => section.querySelector('h2')?.textContent === 'About');
  about?.classList.add('about-section');
  const projects = root.querySelector<HTMLElement>('#projects')!;
  const items = [...projects.querySelectorAll<HTMLAnchorElement>(':scope > a')];
  const grid = document.createElement('div');
  grid.className = 'project-gallery';
  grid.id = 'project-gallery';
  const captions = [
    'ETF optimization, MATLAB cross-checks, and walk-forward testing.',
    'Four Canadian equity portfolios, validated market data, and volatility forecasts.',
    'Property stress tests, debt analysis, and capital allocation scenarios.',
    'Cloud spending, resource utilization, and a prioritized savings queue.',
    'A study of AI operating costs, human labour, and break-even scenarios.',
    'Structured portfolio access for Claude with deterministic calculations.',
    'Invoice review, expense trends, and explainable anomaly detection.',
    'A local desktop assistant for repeatable form filling.',
    'Mobile Python lessons, practice, and progress tracking.',
  ];
  items.forEach((item, i) => {
    item.classList.add('project-tile');
    const description = item.querySelector('h3 + p');
    if (description) description.textContent = captions[i];
    grid.append(item);
  });
  const controls = document.createElement('div');
  controls.className = 'gallery-controls';
  const previous = button('Previous projects', '←');
  const next = button('Next projects', '→');
  previous.setAttribute('aria-controls', grid.id);
  next.setAttribute('aria-controls', grid.id);
  const count = document.createElement('span');
  count.setAttribute('aria-live', 'polite');
  let page = 0;
  const narrow = window.matchMedia('(max-width:900px)');
  function render() {
    const size = narrow.matches ? 1 : 3;
    items.forEach((item, i) => { item.hidden = Math.floor(i / size) !== page; });
    previous.disabled = page === 0;
    next.disabled = (page + 1) * size >= items.length;
    count.textContent = `${page * size + 1}–${Math.min((page + 1) * size, items.length)} of ${items.length} projects`;
    reveal(items.filter(item => !item.hidden));
  }
  narrow.addEventListener('change', () => { page = 0; render(); });
  previous.onclick = () => { page--; render(); };
  next.onclick = () => { page++; render(); };
  controls.append(count, previous, next);
  projects.append(grid, controls);
  render();

  root.querySelectorAll<HTMLElement>('.experience-card').forEach((card) => {
    const details = document.createElement('details');
    details.className = 'experience-disclosure';
    const summary = document.createElement('summary');
    const head = card.querySelector('.experience-head')!;
    summary.append(head);
    const marker = document.createElement('span');
    marker.className = 'disclosure-marker';
    marker.textContent = '+';
    marker.setAttribute('aria-hidden', 'true');
    summary.append(marker);
    const body = document.createElement('div');
    body.className = 'experience-body';
    while (card.firstChild) body.append(card.firstChild);
    details.append(summary, body);
    card.replaceWith(details);
    details.addEventListener('toggle', () => { if (details.open) reveal([body]); });
  });

  const dialog = document.createElement('dialog');
  dialog.className = 'credential-dialog';
  dialog.setAttribute('aria-label', 'Certificate details');
  const close = button('Close certificate details', '×');
  close.className = 'dialog-close';
  const content = document.createElement('div');
  dialog.append(close, content);
  document.body.append(dialog);
  close.onclick = () => dialog.close();
  dialog.onclick = event => { if (event.target === dialog) dialog.close(); };
  root.querySelectorAll<HTMLElement>('.certification-card').forEach(card => {
    const title = card.querySelector('.certification-title h3')!.textContent!;
    const detail = card.querySelector('.certification-detail')!;
    const preview = card.querySelector('.certification-preview img')!;
    const trigger = button(`View ${title}`, 'View details');
    trigger.className = 'credential-trigger';
    card.removeAttribute('tabindex');
    trigger.onclick = () => {
      content.replaceChildren(preview.cloneNode(true), detail.cloneNode(true));
      dialog.showModal();
      reveal([content]);
    };
    card.append(trigger);
  });
  inView(root.querySelectorAll('section'), element => {
    if (!reduced.matches) animate(element, { opacity: [0.96, 1], y: [8, 0] }, { duration: 0.35 });
  });
}

// The existing template runtime mounts the page asynchronously.
function mount() {
  const projects = document.querySelector<HTMLElement>('body #projects');
  if (!projects || projects.closest('x-dc')) return false;
  observer.disconnect();
  enhance(projects.parentElement!);
  return true;
}
const observer = new MutationObserver(mount);
if (!mount()) observer.observe(document.body, { childList: true, subtree: true });
