const styleId = 'talk-table-styles';

function addGlobalStyles() {
    if (document.getElementById(styleId)) {
        return; // Styles already added
    }

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
        talk-table, speaker-table {
            display: block;
            overflow-y: auto;
            border: 1px solid #ccc;
        }

        talk-table table, speaker-table table {
            width: 100%;
            border-collapse: collapse;
        }

        talk-table th, speaker-table th {
            position: sticky;
            top: 0;
            background-color: white;
            padding: 8px;
            border-bottom: 2px solid #ccc;
            text-align: left;
        }

        talk-table th:first-child {
            cursor: pointer;
        }

        talk-table th .sort-indicator {
            display: inline-block;
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            margin-left: 5px;
            vertical-align: middle;
        }

        talk-table th .sort-indicator.asc {
            border-bottom: 5px solid black;
        }

        talk-table th .sort-indicator.desc {
            border-top: 5px solid black;
        }

        talk-table td, speaker-table td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
    `;
    document.head.appendChild(style);
}


class TalkTable extends HTMLElement {
    constructor() {
        super();
        this.sortDirection = 'desc'; // Initial sort direction
    }

    connectedCallback() {
        addGlobalStyles();
        // Defer execution until after the inner HTML has been parsed
        setTimeout(() => {
            const table = this.querySelector('table');
            if (table) {
                if (!table.querySelector('thead')) {
                    const header = document.createElement('thead');
                    header.innerHTML = `
                        <tr>
                            <th>Date <span class="sort-indicator desc"></span></th>
                            <th>Title</th>
                            <th>Speaker</th>
                            <th>Links</th>
                        </tr>
                    `;
                    table.prepend(header);
                }
                const dateHeader = table.querySelector('th:first-child');
                if (dateHeader) {
                    dateHeader.addEventListener('click', () => this.sortTable(table));
                }
            }
        }, 0);
    }

    sortTable(table) {
        // Toggle sort direction first
        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';

        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const indicator = table.querySelector('th:first-child .sort-indicator');

        rows.sort((a, b) => {
            const dateA = new Date(a.cells[0].textContent);
            const dateB = new Date(b.cells[0].textContent);
            if (this.sortDirection === 'asc') {
                return dateA - dateB;
            } else {
                return dateB - dateA;
            }
        });

        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));

        // Update indicator
        if (indicator) {
            indicator.classList.toggle('asc', this.sortDirection === 'asc');
            indicator.classList.toggle('desc', this.sortDirection === 'desc');
        }
    }
}

class SpeakerTable extends HTMLElement {
    connectedCallback() {
        addGlobalStyles();
        // Defer execution until after the inner HTML has been parsed
        setTimeout(() => {
            const table = this.querySelector('table');
            if (table && !table.querySelector('thead')) {
                const header = document.createElement('thead');
                header.innerHTML = `
                    <tr>
                        <th>Speaker</th>
                        <th>Audiodharma Page</th>
                    </tr>
                `;
                table.prepend(header);
            }
        }, 0);
    }
}

customElements.define('talk-table', TalkTable);
customElements.define('speaker-table', SpeakerTable);
