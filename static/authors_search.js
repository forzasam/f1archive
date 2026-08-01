(() => {
    const input = document.getElementById('authors-search-input');
    const cards = Array.from(document.querySelectorAll('[data-author-card]'));
    const count = document.getElementById('authors-result-count');
    const noResults = document.getElementById('authors-no-results');

    if (!input || !cards.length || !count || !noResults) {
        return;
    }

    const normalise = (value) => value.trim().toLocaleLowerCase();

    const updateResults = () => {
        const query = normalise(input.value);
        let visibleCount = 0;

        cards.forEach((card) => {
            const searchableText = normalise(card.dataset.authorSearch || '');
            const matches = !query || searchableText.includes(query);
            card.hidden = !matches;
            if (matches) {
                visibleCount += 1;
            }
        });

        count.textContent = `${visibleCount} author${visibleCount === 1 ? '' : 's'}`;
        noResults.hidden = visibleCount !== 0;
    };

    input.addEventListener('input', updateResults);
    updateResults();
})();
