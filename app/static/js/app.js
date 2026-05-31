document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-nav-toggle]");
    const links = document.querySelector("[data-nav-links]");

    if (toggle && links) {
        toggle.addEventListener("click", () => {
            const isOpen = links.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", String(isOpen));
        });

        links.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                links.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    document.querySelectorAll("[data-file-drop]").forEach((dropZone) => {
        const input = dropZone.querySelector('input[type="file"]');

        if (!input) {
            return;
        }

        let fileName = dropZone.querySelector("[data-file-caption]");
        const selectButton = dropZone.querySelector(".file-select-button");

        if (!fileName) {
            fileName = document.createElement("div");
            fileName.className = "file-drop-name muted small";
            dropZone.appendChild(fileName);
        }

        if (selectButton && !selectButton.dataset.defaultText) {
            selectButton.dataset.defaultText = selectButton.textContent.trim() || "Выберите файл";
        }

        fileName.textContent = "Файл не выбран";

        const updateFileName = () => {
            if (input.files && input.files.length > 0) {
                fileName.textContent = `Выбран файл: ${input.files[0].name}`;
                dropZone.classList.add("has-file");

                if (selectButton) {
                    selectButton.textContent = "Заменить файл";
                }
            } else {
                fileName.textContent = "Файл не выбран";
                dropZone.classList.remove("has-file");

                if (selectButton) {
                    selectButton.textContent = selectButton.dataset.defaultText || "Выберите файл";
                }
            }
        };

        input.addEventListener("change", updateFileName);

        dropZone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dropZone.classList.add("is-dragover");
        });

        dropZone.addEventListener("dragleave", () => {
            dropZone.classList.remove("is-dragover");
        });

        dropZone.addEventListener("drop", (event) => {
            event.preventDefault();
            dropZone.classList.remove("is-dragover");

            if (event.dataTransfer.files.length > 0) {
                input.files = event.dataTransfer.files;
                updateFileName();
            }
        });
    });

    document.querySelectorAll("[data-storage-mode-toggle]").forEach((toggle) => {
        const form = toggle.closest("form");
        const input = form ? form.querySelector("[data-storage-mode-input]") : null;

        if (!input) {
            return;
        }

        const syncStorageMode = () => {
            input.value = toggle.checked ? "temporary" : "no_store";
        };

        toggle.addEventListener("change", syncStorageMode);
        syncStorageMode();
    });

    document.querySelectorAll("[data-paginated-table]").forEach((tableWrap) => {
        const rows = Array.from(tableWrap.querySelectorAll("tbody tr"));
        const pageSize = Number(tableWrap.dataset.pageSize || "10");
        const controls = tableWrap.querySelector("[data-pagination-controls]");
        const prevButton = tableWrap.querySelector("[data-page-prev]");
        const nextButton = tableWrap.querySelector("[data-page-next]");
        const pageInfo = tableWrap.querySelector("[data-page-info]");

        if (!rows.length || !controls || !prevButton || !nextButton || !pageInfo) {
            return;
        }

        const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
        let currentPage = 1;

        const renderPage = () => {
            tableWrap.classList.add("is-switching");

            window.setTimeout(() => {
                rows.forEach((row, index) => {
                    const start = (currentPage - 1) * pageSize;
                    const end = start + pageSize;
                    row.hidden = index < start || index >= end;
                });

                pageInfo.textContent = `Страница ${currentPage} из ${totalPages}`;
                prevButton.disabled = currentPage === 1;
                nextButton.disabled = currentPage === totalPages;

                tableWrap.classList.remove("is-switching");
            }, 120);
        };

        prevButton.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage -= 1;
                renderPage();
            }
        });

        nextButton.addEventListener("click", () => {
            if (currentPage < totalPages) {
                currentPage += 1;
                renderPage();
            }
        });

        renderPage();
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", () => {
            const submitButton = form.querySelector('button[type="submit"]');

            if (!submitButton) {
                return;
            }

            if (form.dataset.confirmedSubmit === "true") {
                return;
            }

            form.dataset.confirmedSubmit = "true";
            submitButton.classList.add("is-loading");
            submitButton.setAttribute("aria-busy", "true");

            const originalText = submitButton.textContent;
            submitButton.dataset.originalText = originalText || "";
            submitButton.textContent = "Выполняется...";
        });
    });
});