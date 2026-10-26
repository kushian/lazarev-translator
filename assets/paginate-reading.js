window.paginateReading = async function () {
  await document.fonts.ready;
  const main = document.querySelector('main');
  const queue = [...main.children];
  const original = queue.map(e=>e.textContent).join(' ').replace(/\s+/g, ' ').trim();
  main.replaceChildren();
  document.body.classList.add('paginated');
  let content;
  function newPage() {
    const sheet = document.createElement('section');
    sheet.className = 'a4-page';
    content = document.createElement('div');
    content.className = 'page-content';
    const footer = document.createElement('div');
    footer.className = 'page-number';
    footer.textContent = String(main.children.length + 1);
    sheet.append(content, footer);
    main.append(sheet);
  }
  function fits() {
    return [...content.children].every(e => e.getBoundingClientRect().bottom <= content.getBoundingClientRect().bottom + .1);
  }
  function position(node, offset) {
    const walk = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    let text;
    while ((text = walk.nextNode())) {
      if (offset <= text.length) return [text, offset];
      offset -= text.length;
    }
    return [node, node.childNodes.length];
  }
  function slice(node, start, end) {
    const range = document.createRange();
    range.setStart(...position(node, start));
    range.setEnd(...position(node, end));
    const clone = node.cloneNode(false);
    clone.append(range.cloneContents());
    return clone;
  }
  newPage();
  let iterations = 0;
  // Each block costs at least one pass, plus a few for splits and moved headings. A fixed cap
  // (1200) broke whole books with thousands of paragraphs; scale it with the document instead.
  const maxIterations = Math.max(1200, queue.length * 12);
  while (queue.length) {
    if (++iterations > maxIterations) throw new Error('Pagination loop: '+queue.slice(0,2).map(e=>e.tagName+':'+e.textContent.slice(0,100)).join(' / ')+'; content height '+content.getBoundingClientRect().height);
    const node = queue.shift();
    content.append(node);
    if (fits()) continue;
    node.remove();
    if (node.tagName === 'P' && !node.classList.contains('question')) {
      const text = node.textContent;
      const boundaries = [...text.matchAll(/\s+/g)].map(m => m.index + m[0].length);
      let low = 0, high = boundaries.length - 1, best = -1;
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const trial = slice(node, 0, boundaries[mid]);
        content.append(trial);
        const good = fits();
        trial.remove();
        if (good) { best = mid; low = mid + 1; } else high = mid - 1;
      }
      if (best >= 0) {
        const cut = boundaries[best];
        const first = slice(node, 0, cut);
        content.append(first);
        const line = parseFloat(getComputedStyle(first).lineHeight);
        // Avoid placing a single continuation line at the bottom of a page.
        if (first.getBoundingClientRect().height >= line * 2.8) {
          first.classList.add('continues');
          queue.unshift(slice(node, cut, text.length));
          newPage();
          continue;
        }
        first.remove();
      }
    }
    if (!content.children.length) throw new Error('Block exceeds A4 content area: '+node.tagName);
    const last = content.lastElementChild;
    // keep-with-next: headings, questions, and short lead-in lines ending with a colon
    const leadIn = last.tagName === 'P' && last.textContent.trim().length < 120 && /[:：]\s*$/.test(last.textContent);
    if ((/^H[1-6]$/.test(last.tagName) || last.classList.contains('question') || leadIn) && content.children.length > 1) {
      last.remove();
      queue.unshift(node);
      queue.unshift(last);
    } else queue.unshift(node);
    newPage();
  }
  const after = [...main.querySelectorAll('.page-content')].flatMap(e=>[...e.children]).map(e=>e.textContent).join(' ').replace(/\s+/g, ' ').trim();
  if (original !== after) throw new Error('Pagination changed text');
  return {pages:main.children.length,textPreserved:true};
};
