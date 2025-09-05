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

        talk-table td, speaker-table td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
    `;
    document.head.appendChild(style);
}


class TalkTable extends HTMLElement {
    connectedCallback() {
        addGlobalStyles();
        // Defer execution until after the inner HTML has been parsed
        setTimeout(() => {
            const table = this.querySelector('table');
            if (table && !table.querySelector('thead')) {
                const header = document.createElement('thead');
                header.innerHTML = `
                    <tr>
                        <th>Date</th>
                        <th>Title</th>
                        <th>Speaker</th>
                        <th>Links</th>
                    </tr>
                `;
                table.prepend(header);
            }
        }, 0);
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
                        <th>Talks processed here</th>
                    </tr>
                `;
                table.prepend(header);
            }
        }, 0);
    }
}

customElements.define('talk-table', TalkTable);
customElements.define('speaker-table', SpeakerTable);
