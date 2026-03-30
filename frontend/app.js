const form = document.getElementById('uploadForm');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');

const statLabels = {
  kills: 'Убийства',
  deaths: 'Смерти',
  assists: 'Ассисты',
  headshot_percent: 'HS %',
  adr: 'ADR',
  utility_damage: 'Utility урон',
  opening_duel_success_percent: 'Winrate первых дуэлей %',
  clutch_success_percent: 'Clutch success %',
};

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const input = document.getElementById('demoFile');
  const file = input.files?.[0];
  if (!file) {
    statusEl.textContent = 'Выберите файл .dem';
    return;
  }

  const body = new FormData();
  body.append('file', file);

  statusEl.textContent = 'Идет анализ...';
  resultsEl.classList.add('hidden');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ?? 'Ошибка анализа');
    }

    renderResult(data);
    statusEl.textContent = 'Анализ завершен.';
  } catch (error) {
    statusEl.textContent = `Ошибка: ${error.message}`;
  }
});

function renderResult(data) {
  const summary = `
    <div class="block">
      <h2>Матч: ${data.file}</h2>
      <p>Карта: <strong>${data.summary.map}</strong>, раундов: <strong>${data.summary.rounds}</strong></p>
      <p>Impact score: <strong>${data.summary.impact_score}</strong>/100</p>
    </div>
  `;

  const stats = Object.entries(data.stats)
    .map(([key, value]) => `<div class="tile"><strong>${statLabels[key] ?? key}</strong><br>${value}</div>`)
    .join('');

  const mistakes = data.mistakes
    .map((m) => `<li><strong>${m.title}:</strong> ${m.details}</li>`)
    .join('');

  const recommendations = data.recommendations
    .map((r) => `<li>${r}</li>`)
    .join('');

  resultsEl.innerHTML = `
    ${summary}
    <div class="block">
      <h3>Ключевая статистика</h3>
      <div class="grid">${stats}</div>
    </div>
    <div class="block">
      <h3>Ошибки</h3>
      <ul>${mistakes}</ul>
    </div>
    <div class="block">
      <h3>Рекомендации от ИИ</h3>
      <ul>${recommendations}</ul>
    </div>
  `;

  resultsEl.classList.remove('hidden');
}
