class TalkTable extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const table = this.querySelector('table');
        if (table) {
            this.enhanceTable(table);
        }
    }

    enhanceTable(table) {
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
}

class SpeakerTable extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const table = this.querySelector('table');
        if (table) {
            this.enhanceTable(table);
        }
    }

    enhanceTable(table) {
        const header = document.createElement('thead');
        header.innerHTML = `
            <tr>
                <th>Speaker</th>
                <th>Number of Talks</th>
            </tr>
        `;
        table.prepend(header);
    }
}

customElements.define('talk-table', TalkTable);
customElements.define('speaker-table', SpeakerTable);
