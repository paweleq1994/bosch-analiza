"use strict";

(function () {
    const polishCollator = new Intl.Collator("pl", {
        numeric: true,
        sensitivity: "base",
    });
    const missingLabels = new Set(["", "—", "–", "-", "brak", "n/d", "n/a", "null", "nan", "nie dotyczy"]);
    const numericKinds = new Set(["number", "date"]);

    function parseNumericValue(value) {
        const normalizedValue = value.replace(/[\u00a0\u202f\s]/g, "").replace(/(?:zł|pln|%|pkt)\.?$/i, "");

        if (/^[+-]?\d+\.$/.test(normalizedValue)) {
            return Number(normalizedValue.slice(0, -1));
        }

        if (/^[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(normalizedValue)) {
            return Number(normalizedValue.replace(/\./g, "").replace(",", "."));
        }

        if (/^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$/.test(normalizedValue)) {
            return Number(normalizedValue.replace(/,/g, ""));
        }

        if (/^[+-]?\d+(?:[.,]\d+)?$/.test(normalizedValue)) {
            return Number(normalizedValue.replace(",", "."));
        }

        return null;
    }

    function parseSortValue(rawValue) {
        const originalValue = String(rawValue ?? "").replace(/[\u00a0\u202f]/g, " ").trim();

        if (missingLabels.has(originalValue.toLocaleLowerCase("pl"))) {
            return {kind: "missing", value: null, original: originalValue};
        }

        const isoDate = originalValue.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2})?.*)?$/);
        const polishDate = originalValue.match(/^(\d{2})[./-](\d{2})[./-](\d{4})$/);

        if (isoDate || polishDate) {
            const year = Number(isoDate ? isoDate[1] : polishDate[3]);
            const month = Number(isoDate ? isoDate[2] : polishDate[2]);
            const day = Number(isoDate ? isoDate[3] : polishDate[1]);

            if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
                return {kind: "date", value: year * 10000 + month * 100 + day, original: originalValue};
            }
        }

        const score = originalValue.match(/^(\d+)\s*:\s*(\d+)$/);

        if (score) {
            const goalsFor = Number(score[1]);
            const goalsAgainst = Number(score[2]);

            return {
                kind: "score",
                value: [goalsFor - goalsAgainst, goalsFor, -goalsAgainst],
                original: originalValue,
            };
        }

        const numberValue = parseNumericValue(originalValue);

        if (numberValue !== null && Number.isFinite(numberValue)) {
            return {kind: "number", value: numberValue, original: originalValue};
        }

        return {kind: "text", value: originalValue, original: originalValue};
    }

    function compareSortValues(first, second, direction = "asc") {
        if (first.kind === "missing" || second.kind === "missing") {
            if (first.kind === second.kind) {
                return 0;
            }

            return first.kind === "missing" ? 1 : -1;
        }

        let comparison = 0;

        if (first.kind === second.kind && numericKinds.has(first.kind)) {
            comparison = first.value - second.value;
        } else if (first.kind === "score" && second.kind === "score") {
            for (let index = 0; index < first.value.length; index += 1) {
                comparison = first.value[index] - second.value[index];

                if (comparison !== 0) {
                    break;
                }
            }
        } else {
            comparison = polishCollator.compare(first.original, second.original);
        }

        const normalizedComparison = Math.sign(comparison);

        return direction === "desc" ? -normalizedComparison : normalizedComparison;
    }

    function getCellSortValue(row, columnIndex) {
        const cell = row.cells[columnIndex];
        const value = cell?.dataset?.sortValue ?? cell?.textContent ?? "";

        return parseSortValue(value);
    }

    function sortTableBody(body, columnIndex, direction) {
        const rows = Array.from(body.rows || []);
        const indexedRows = rows.map((row, originalIndex) => ({
            row,
            originalIndex,
            value: getCellSortValue(row, columnIndex),
        }));

        indexedRows.sort((first, second) => {
            return compareSortValues(first.value, second.value, direction) || first.originalIndex - second.originalIndex;
        });

        body.append(...indexedRows.map(entry => entry.row));

        return indexedRows.map(entry => entry.row);
    }

    function defaultDirection(header, table, columnIndex) {
        const heading = String(header.textContent || "").trim().toLocaleLowerCase("pl");

        if (/^(#|lp\.?|l\.p\.?|miejsce|pozycja|ranking|lokata)$/.test(heading)) {
            return "asc";
        }

        if (/^(data|dzień|termin)$/.test(heading)) {
            return "desc";
        }

        const body = Array.from(table.tBodies || []).find(section => section.rows.length > 0);
        const firstRow = body?.rows?.[0];
        const kind = firstRow ? getCellSortValue(firstRow, columnIndex).kind : "text";

        return kind === "number" || kind === "score" || kind === "date" ? "desc" : "asc";
    }

    function enhanceTable(table) {
        if (table.dataset.sortEnhanced === "true" || table.dataset.sortDisabled === "true") {
            return false;
        }

        const headerRow = table.tHead?.rows?.[table.tHead.rows.length - 1];

        if (!headerRow || !table.tBodies?.length || table.querySelector('thead button[data-key], thead button[data-sort]')) {
            return false;
        }

        const sortableHeaders = [];
        let columnIndex = 0;

        for (const header of Array.from(headerRow.cells)) {
            const currentColumn = columnIndex;
            columnIndex += header.colSpan || 1;

            if (header.tagName !== "TH" || header.colSpan > 1 || header.rowSpan > 1 || header.querySelector("button, input, select, a")) {
                continue;
            }

            sortableHeaders.push({header, columnIndex: currentColumn});
        }

        if (!sortableHeaders.length) {
            return false;
        }

        table.dataset.sortEnhanced = "true";

        for (const {header, columnIndex: currentColumn} of sortableHeaders) {
            const title = String(header.textContent || "").trim();
            const button = document.createElement("button");
            const icon = document.createElement("span");

            button.type = "button";
            button.className = "table-sort-button";
            button.setAttribute("aria-label", "Sortuj według kolumny: " + title);
            icon.className = "table-sort-indicator";
            icon.setAttribute("aria-hidden", "true");
            icon.textContent = "↕";

            while (header.firstChild) {
                button.appendChild(header.firstChild);
            }

            button.appendChild(icon);
            header.appendChild(button);
            header.setAttribute("scope", "col");
            header.setAttribute("aria-sort", "none");

            button.addEventListener("click", () => {
                const previousColumn = Number(table.dataset.sortColumn);
                const previousDirection = table.dataset.sortDirection;
                const direction = previousDirection && previousColumn === currentColumn
                    ? (previousDirection === "asc" ? "desc" : "asc")
                    : defaultDirection(header, table, currentColumn);

                for (const item of sortableHeaders) {
                    const isActive = item.columnIndex === currentColumn;

                    item.header.setAttribute("aria-sort", isActive ? (direction === "asc" ? "ascending" : "descending") : "none");
                    item.header.querySelector(".table-sort-indicator").textContent = isActive ? (direction === "asc" ? "↑" : "↓") : "↕";
                }

                table.dataset.sortColumn = String(currentColumn);
                table.dataset.sortDirection = direction;

                for (const body of Array.from(table.tBodies)) {
                    sortTableBody(body, currentColumn, direction);
                }
            });
        }

        return true;
    }

    function enhanceTables(root) {
        if (root.nodeType !== 1) {
            return;
        }

        if (root.matches?.("table")) {
            enhanceTable(root);
        }

        for (const table of root.querySelectorAll?.("table") || []) {
            enhanceTable(table);
        }
    }

    function initialise() {
        enhanceTables(document.body);

        const observer = new MutationObserver(records => {
            for (const record of records) {
                for (const node of record.addedNodes) {
                    enhanceTables(node);
                }
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {parseSortValue, compareSortValues, sortTableBody, enhanceTable};
    }

    if (typeof document !== "undefined") {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initialise, {once: true});
        } else {
            initialise();
        }
    }
})();
