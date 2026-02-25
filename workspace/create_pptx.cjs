const globalModules = 'C:/Users/uma92/.npm-global/node_modules';
const pptxgen = require(globalModules + '/pptxgenjs');
const path = require('path');
const html2pptx = require('C:/Users/uma92/.claude/plugins/cache/anthropic-agent-skills/document-skills/69c0b1a06741/skills/pptx/scripts/html2pptx');

// Studio data
const studios = {
  domestic: [
    { name: "東映アニメ", score: 0.55, foundedSize: 35, currentSize: 960 },
    { name: "トムス", score: 0.15, foundedSize: 10, currentSize: 307 },
    { name: "BNフィルムワークス", score: 0.65, foundedSize: 7, currentSize: 646 },
    { name: "Production I.G", score: 0.50, foundedSize: 10, currentSize: 219 },
    { name: "ufotable", score: 0.15, foundedSize: 5, currentSize: 256 },
    { name: "MAPPA", score: 0.35, foundedSize: 10, currentSize: 467 },
    { name: "WIT STUDIO", score: 0.40, foundedSize: 10, currentSize: 320 },
    { name: "CloverWorks", score: 0.15, foundedSize: 100, currentSize: 240 },
    { name: "A-1 Pictures", score: 0.15, foundedSize: 30, currentSize: 250 },
    { name: "京都アニメ", score: 0.80, foundedSize: 5, currentSize: 188 },
    { name: "シャフト", score: 0.20, foundedSize: 5, currentSize: 100 },
    { name: "ボンズ", score: 0.50, foundedSize: 8, currentSize: 119 },
    { name: "マッドハウス", score: 0.20, foundedSize: 4, currentSize: 70 },
    { name: "ポリゴンP", score: 0.15, foundedSize: 5, currentSize: 300 },
    { name: "オレンジ", score: 0.20, foundedSize: 5, currentSize: 170 },
    { name: "Science SARU", score: 0.55, foundedSize: 4, currentSize: 51 },
    { name: "Colorido", score: 0.75, foundedSize: 5, currentSize: 40 },
    { name: "ツインエンジン", score: 0.80, foundedSize: 2, currentSize: 107 },
  ],
  international: [
    { name: "Pixar", score: 0.95, foundedSize: 40, currentSize: 1100 },
    { name: "DreamWorks", score: 0.90, foundedSize: 250, currentSize: 2700 },
    { name: "Illumination", score: 0.90, foundedSize: 10, currentSize: 800 },
    { name: "Powerhouse", score: 0.40, foundedSize: 3, currentSize: 130 },
    { name: "Titmouse", score: 0.15, foundedSize: 2, currentSize: 1200 },
    { name: "Cartoon Saloon", score: 0.85, foundedSize: 3, currentSize: 300 },
    { name: "Fortiche", score: 0.45, foundedSize: 3, currentSize: 240 },
    { name: "DR Movie", score: 0.05, foundedSize: 20, currentSize: 400 },
    { name: "Studio Mir", score: 0.15, foundedSize: 20, currentSize: 120 },
    { name: "Haoliners", score: 0.40, foundedSize: 5, currentSize: 200 },
    { name: "Tonko House", score: 0.90, foundedSize: 2, currentSize: 20 },
  ]
};

// Key studios for growth trajectory (slide 4)
const trajectoryStudios = {
  domestic: [
    "東映アニメ", "BNフィルムワークス", "MAPPA", "WIT STUDIO",
    "京都アニメ", "ボンズ", "ツインエンジン", "Science SARU", "ufotable", "ポリゴンP"
  ],
  international: [
    "Pixar", "DreamWorks", "Titmouse", "Cartoon Saloon",
    "Fortiche", "Tonko House", "Powerhouse", "Studio Mir"
  ]
};

// Map coordinate system
const MAP = {
  x: 0.8, y: 1.15, w: 8.4, h: 4.1,
  // Axis range
  xMin: -0.05, xMax: 1.05,
  yMin: Math.log10(1.5), yMax: Math.log10(4000),
};

function scoreToX(score) {
  return MAP.x + ((score - MAP.xMin) / (MAP.xMax - MAP.xMin)) * MAP.w;
}

function sizeToY(size) {
  const logSize = Math.log10(Math.max(size, 2));
  return MAP.y + MAP.h - ((logSize - MAP.yMin) / (MAP.yMax - MAP.yMin)) * MAP.h;
}

function addAxes(slide) {
  // Horizontal axis line (center)
  slide.addShape('line', {
    x: MAP.x, y: MAP.y + MAP.h / 2,
    w: MAP.w, h: 0,
    line: { color: '999999', width: 1.5 }
  });
  // Vertical axis line (center)
  slide.addShape('line', {
    x: MAP.x + MAP.w / 2, y: MAP.y,
    w: 0, h: MAP.h,
    line: { color: '999999', width: 1.5 }
  });
  // Border box
  slide.addShape('rect', {
    x: MAP.x, y: MAP.y, w: MAP.w, h: MAP.h,
    line: { color: 'CCCCCC', width: 0.75 },
    fill: { type: 'none' }
  });

  // Axis labels
  slide.addText('受託メイン', { x: MAP.x - 0.1, y: MAP.y + MAP.h + 0.05, w: 1.2, h: 0.25, fontSize: 8, color: '555555', align: 'left' });
  slide.addText('オリジナルメイン', { x: MAP.x + MAP.w - 1.1, y: MAP.y + MAP.h + 0.05, w: 1.2, h: 0.25, fontSize: 8, color: '555555', align: 'right' });

  // Y axis labels (log scale)
  const yTicks = [2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000];
  yTicks.forEach(val => {
    const yPos = sizeToY(val);
    if (yPos >= MAP.y && yPos <= MAP.y + MAP.h) {
      slide.addText(val >= 1000 ? `${val/1000}K` : `${val}`, {
        x: MAP.x - 0.55, y: yPos - 0.1, w: 0.5, h: 0.2,
        fontSize: 7, color: '888888', align: 'right'
      });
      // Gridline
      slide.addShape('line', {
        x: MAP.x, y: yPos, w: MAP.w, h: 0,
        line: { color: 'EEEEEE', width: 0.5, dashType: 'dash' }
      });
    }
  });
  slide.addText('人数', { x: MAP.x - 0.6, y: MAP.y - 0.25, w: 0.5, h: 0.2, fontSize: 8, color: '555555', align: 'right' });
}

function addDots(slide, useFoundedSize, showLabels = true) {
  const dotSize = 0.13;
  const allDots = [];

  // Domestic studios (blue)
  studios.domestic.forEach(s => {
    const size = useFoundedSize ? s.foundedSize : s.currentSize;
    const cx = scoreToX(s.score);
    const cy = sizeToY(size);
    allDots.push({ ...s, cx, cy, color: '3498DB', region: 'domestic' });

    slide.addShape('oval', {
      x: cx - dotSize / 2, y: cy - dotSize / 2, w: dotSize, h: dotSize,
      fill: { color: '3498DB' },
      line: { color: '2980B9', width: 0.5 },
      shadow: { type: 'outer', blur: 2, offset: 1, color: '000000', opacity: 0.2 }
    });
  });

  // International studios (red)
  studios.international.forEach(s => {
    const size = useFoundedSize ? s.foundedSize : s.currentSize;
    const cx = scoreToX(s.score);
    const cy = sizeToY(size);
    allDots.push({ ...s, cx, cy, color: 'E74C3C', region: 'international' });

    slide.addShape('oval', {
      x: cx - dotSize / 2, y: cy - dotSize / 2, w: dotSize, h: dotSize,
      fill: { color: 'E74C3C' },
      line: { color: 'C0392B', width: 0.5 },
      shadow: { type: 'outer', blur: 2, offset: 1, color: '000000', opacity: 0.2 }
    });
  });

  if (showLabels) {
    // Add labels with offset to avoid overlap
    allDots.forEach((d, i) => {
      const offsetX = 0.08;
      const offsetY = -0.12;
      slide.addText(d.name, {
        x: d.cx + offsetX, y: d.cy + offsetY, w: 1.2, h: 0.18,
        fontSize: 5.5, color: d.region === 'domestic' ? '2C3E50' : '922B21',
        align: 'left', fontFace: 'Arial'
      });
    });
  }
}

function addLegendMini(slide) {
  const lx = MAP.x + MAP.w - 2.2, ly = MAP.y + 0.1;
  slide.addShape('rect', {
    x: lx, y: ly, w: 2.1, h: 0.5,
    fill: { color: 'FFFFFF' },
    line: { color: 'CCCCCC', width: 0.5 },
    shadow: { type: 'outer', blur: 2, offset: 1, color: '000000', opacity: 0.1 }
  });
  slide.addShape('oval', { x: lx + 0.1, y: ly + 0.08, w: 0.1, h: 0.1, fill: { color: '3498DB' } });
  slide.addText('国内スタジオ', { x: lx + 0.25, y: ly + 0.03, w: 0.8, h: 0.18, fontSize: 7, color: '333333' });
  slide.addShape('oval', { x: lx + 1.1, y: ly + 0.08, w: 0.1, h: 0.1, fill: { color: 'E74C3C' } });
  slide.addText('海外スタジオ', { x: lx + 1.25, y: ly + 0.03, w: 0.8, h: 0.18, fontSize: 7, color: '333333' });

  slide.addShape('oval', { x: lx + 0.1, y: ly + 0.28, w: 0.1, h: 0.1, fill: { color: 'F1C40F' } });
  slide.addText('当社（提案）', { x: lx + 0.25, y: ly + 0.23, w: 0.8, h: 0.18, fontSize: 7, color: '333333' });
}

async function createPresentation() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'AIアニメスタジオ';
  pptx.title = 'ブランディング戦略リサーチ - ポジショニングマップ';

  const slidesDir = path.resolve(__dirname, 'slides');
  const outputPath = path.resolve(__dirname, '..', 'positioning_map.pptx');

  // Slide 1: Title
  await html2pptx(path.join(slidesDir, 'slide1.html'), pptx);

  // Slide 2: Positioning Map (Founded)
  const { slide: slide2 } = await html2pptx(path.join(slidesDir, 'slide2.html'), pptx);
  addAxes(slide2);
  addDots(slide2, true);
  addLegendMini(slide2);

  // Slide 3: Positioning Map (Current)
  const { slide: slide3 } = await html2pptx(path.join(slidesDir, 'slide3.html'), pptx);
  addAxes(slide3);
  addDots(slide3, false);
  addLegendMini(slide3);

  // Add comment boxes for slide 3
  // Dense area comment - commission zone
  slide3.addShape('rect', {
    x: scoreToX(0.1) - 0.3, y: sizeToY(350) - 0.15,
    w: 1.6, h: 0.3,
    fill: { color: 'FFF9C4' },
    line: { color: 'F9A825', width: 0.75 },
    rectRadius: 0.05
  });
  slide3.addText('受託ゾーン: 競合密集', {
    x: scoreToX(0.1) - 0.3, y: sizeToY(350) - 0.15,
    w: 1.6, h: 0.3,
    fontSize: 7, color: '795548', align: 'center', valign: 'middle'
  });

  // Empty area comment - small original
  slide3.addShape('rect', {
    x: scoreToX(0.85) - 0.1, y: sizeToY(80) - 0.15,
    w: 1.6, h: 0.3,
    fill: { color: 'E8F5E9' },
    line: { color: '4CAF50', width: 0.75 },
    rectRadius: 0.05
  });
  slide3.addText('空白地帯: AI活用の機会', {
    x: scoreToX(0.85) - 0.1, y: sizeToY(80) - 0.15,
    w: 1.6, h: 0.3,
    fontSize: 7, color: '2E7D32', align: 'center', valign: 'middle'
  });

  // Slide 4: Growth Trajectory
  const { slide: slide4 } = await html2pptx(path.join(slidesDir, 'slide4.html'), pptx);
  addAxes(slide4);

  // Add trajectory arrows for selected studios
  const allStudios = [...studios.domestic, ...studios.international];
  const filteredStudios = allStudios.filter(s =>
    trajectoryStudios.domestic.includes(s.name) || trajectoryStudios.international.includes(s.name)
  );

  filteredStudios.forEach(s => {
    const isDomestic = studios.domestic.includes(s);
    const color = isDomestic ? '3498DB' : 'E74C3C';
    const startX = scoreToX(s.score);
    const startY = sizeToY(s.foundedSize);
    const endX = scoreToX(s.score);
    const endY = sizeToY(s.currentSize);

    // Start dot (small, faded)
    slide4.addShape('oval', {
      x: startX - 0.04, y: startY - 0.04, w: 0.08, h: 0.08,
      fill: { color: color },
      line: { type: 'none' }
    });
    // End dot (larger)
    slide4.addShape('oval', {
      x: endX - 0.065, y: endY - 0.065, w: 0.13, h: 0.13,
      fill: { color: color },
      line: { color: isDomestic ? '2980B9' : 'C0392B', width: 0.5 }
    });
    // Arrow line
    const lineH = endY - startY;
    slide4.addShape('line', {
      x: startX, y: startY, w: 0, h: lineH,
      line: { color: color, width: 1, dashType: 'dash' }
    });
    // Label at end position
    slide4.addText(s.name, {
      x: endX + 0.08, y: endY - 0.08, w: 1.1, h: 0.16,
      fontSize: 5.5, color: isDomestic ? '2C3E50' : '922B21',
      align: 'left'
    });
  });
  addLegendMini(slide4);

  // Slide 5: Our Positioning Proposal
  const { slide: slide5 } = await html2pptx(path.join(slidesDir, 'slide5.html'), pptx);
  addAxes(slide5);
  addDots(slide5, false, false); // No labels for cleaner look

  // Our proposed position - highlighted
  const ourScore = 0.75;
  const ourSize = 15;
  const ourX = scoreToX(ourScore);
  const ourY = sizeToY(ourSize);

  // Highlight circle (large, semi-transparent)
  slide5.addShape('oval', {
    x: ourX - 0.35, y: ourY - 0.35, w: 0.7, h: 0.7,
    fill: { color: 'F1C40F' },
    line: { color: 'F39C12', width: 2 },
    shadow: { type: 'outer', blur: 5, offset: 2, color: '000000', opacity: 0.3 }
  });
  slide5.addText('当社', {
    x: ourX - 0.35, y: ourY - 0.1, w: 0.7, h: 0.2,
    fontSize: 8, color: '1C2833', align: 'center', bold: true
  });

  // Proposed direction arrow area
  slide5.addShape('rect', {
    x: 0.5, y: MAP.y + MAP.h - 1.6, w: 2.8, h: 1.5,
    fill: { color: 'F8F9FA' },
    line: { color: '3498DB', width: 1 },
    rectRadius: 0.1
  });
  slide5.addText([
    { text: '提案ポジション\n', options: { bold: true, fontSize: 9, color: '1C2833' } },
    { text: '小規模 × オリジナル制作\n', options: { fontSize: 8, color: '2C3E50' } },
    { text: '\n', options: { fontSize: 4 } },
    { text: 'AI技術による制作効率化で\n', options: { fontSize: 7, color: '555555' } },
    { text: '少人数でもオリジナルIP創出が可能\n', options: { fontSize: 7, color: '555555' } },
    { text: '\n', options: { fontSize: 4 } },
    { text: '競合: Tonko House, Colorido\n', options: { fontSize: 6.5, color: '888888' } },
    { text: '差別化: AI活用による生産性', options: { fontSize: 6.5, color: '3498DB', bold: true } },
  ], {
    x: 0.6, y: MAP.y + MAP.h - 1.5, w: 2.6, h: 1.3,
    valign: 'top'
  });

  addLegendMini(slide5);

  // Slide 6: Legend & Sources
  await html2pptx(path.join(slidesDir, 'slide6.html'), pptx);

  // Save
  await pptx.writeFile({ fileName: outputPath });
  console.log(`Presentation saved to: ${outputPath}`);
}

createPresentation().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
