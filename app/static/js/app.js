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

        const fileName = document.createElement("div");
        fileName.className = "file-drop-name muted small";
        fileName.textContent = "Файл не выбран";
        dropZone.appendChild(fileName);

        const updateFileName = () => {
            if (input.files && input.files.length > 0) {
                fileName.textContent = `Выбран файл: ${input.files[0].name}`;
                dropZone.classList.add("has-file");
            } else {
                fileName.textContent = "Файл не выбран";
                dropZone.classList.remove("has-file");
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