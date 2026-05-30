document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-nav-toggle]");
    const links = document.querySelector("[data-nav-links]");

    if (toggle && links) {
        toggle.addEventListener("click", () => {
            links.classList.toggle("is-open");
        });
    }

    document.querySelectorAll("[data-file-drop]").forEach((dropZone) => {
        const input = dropZone.querySelector('input[type="file"]');

        if (!input) {
            return;
        }

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
            }
        });
    });
});