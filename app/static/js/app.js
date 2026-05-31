document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-nav-toggle]");
    const links = document.querySelector("[data-nav-links]");

    if (toggle && links) {
        const backdrop = document.createElement("div");
        backdrop.className = "mobile-nav-backdrop";
        backdrop.setAttribute("data-nav-backdrop", "");
        document.body.appendChild(backdrop);

        const openMenu = () => {
            links.classList.add("is-open");
            toggle.setAttribute("aria-expanded", "true");
            document.body.classList.add("mobile-nav-open");
            links.setAttribute("aria-hidden", "false");
        };

        const closeMenu = () => {
            links.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            document.body.classList.remove("mobile-nav-open");
            links.setAttribute("aria-hidden", "true");
        };

        const toggleMenu = () => {
            if (links.classList.contains("is-open")) {
                closeMenu();
            } else {
                openMenu();
            }
        };

        links.setAttribute("aria-hidden", "true");

        toggle.addEventListener("click", toggleMenu);
        backdrop.addEventListener("click", closeMenu);

        links.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", closeMenu);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && links.classList.contains("is-open")) {
                closeMenu();
            }
        });

        window.addEventListener("resize", () => {
            if (window.innerWidth > 860) {
                closeMenu();
            }
        });
    }

    const formatLocalDatetime = (isoValue) => {
        if (!isoValue) {
            return "—";
        }

        const date = new Date(isoValue);

        if (Number.isNaN(date.getTime())) {
            return "—";
        }

        const now = new Date();

        const dateOnly = new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        );

        const todayOnly = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate()
        );

        const yesterdayOnly = new Date(todayOnly);
        yesterdayOnly.setDate(todayOnly.getDate() - 1);

        const time = date.toLocaleTimeString("ru-RU", {
            hour: "2-digit",
            minute: "2-digit",
        });

        if (dateOnly.getTime() === todayOnly.getTime()) {
            return `Сегодня, в ${time}`;
        }

        if (dateOnly.getTime() === yesterdayOnly.getTime()) {
            return `Вчера, в ${time}`;
        }

        const day = date.toLocaleDateString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });

        return `${day}, ${time}`;
    };

    document.querySelectorAll("[data-local-datetime]").forEach((element) => {
        element.textContent = formatLocalDatetime(element.dataset.localDatetime);
    });

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
            selectButton.dataset.defaultText =
                selectButton.textContent.trim() || "Выберите файл";
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
                    selectButton.textContent =
                        selectButton.dataset.defaultText || "Выберите файл";
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

    const contactModal = document.querySelector("[data-contact-modal]");
    const contactForm = document.querySelector("[data-contact-form]");

    const closeContactModal = () => {
        if (!contactModal) {
            return;
        }

        contactModal.hidden = true;
        document.body.classList.remove("modal-open");
    };

    const openContactModal = () => {
        if (!contactModal) {
            return;
        }

        contactModal.hidden = false;
        document.body.classList.add("modal-open");

        const firstField = contactModal.querySelector("select, textarea, input, button");

        if (firstField) {
            firstField.focus();
        }
    };

    document.querySelectorAll("[data-contact-modal-open]").forEach((button) => {
        button.addEventListener("click", openContactModal);
    });

    document.querySelectorAll("[data-contact-modal-close]").forEach((button) => {
        button.addEventListener("click", closeContactModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && contactModal && !contactModal.hidden) {
            closeContactModal();
        }
    });

    if (contactForm) {
        const contactStatus = contactForm.querySelector("[data-contact-status]");
        const contactSubmitButton = contactForm.querySelector('button[type="submit"]');

        const setContactStatus = (message, type = "success") => {
            if (!contactStatus) {
                return;
            }

            contactStatus.hidden = false;
            contactStatus.textContent = message;
            contactStatus.classList.remove("success", "error");
            contactStatus.classList.add(type);
        };

        const resetContactStatus = () => {
            if (!contactStatus) {
                return;
            }

            contactStatus.hidden = true;
            contactStatus.textContent = "";
            contactStatus.classList.remove("success", "error");
        };

        contactForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();

            resetContactStatus();

            if (contactSubmitButton) {
                contactSubmitButton.disabled = true;
                contactSubmitButton.setAttribute("aria-busy", "true");
                contactSubmitButton.dataset.originalText =
                    contactSubmitButton.textContent || "Отправить письмо";
                contactSubmitButton.textContent = "Отправка...";
            }

            try {
                const response = await fetch(contactForm.action, {
                    method: "POST",
                    body: new FormData(contactForm),
                    headers: {
                        "Accept": "application/json",
                    },
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.message || "Не удалось отправить письмо.");
                }

                setContactStatus(data.message || "Письмо отправлено.", "success");
                contactForm.reset();

                window.setTimeout(() => {
                    closeContactModal();
                    resetContactStatus();
                }, 1400);
            } catch (error) {
                setContactStatus(
                    error.message || "Не удалось отправить письмо. Попробуйте позже.",
                    "error"
                );
            } finally {
                if (contactSubmitButton) {
                    contactSubmitButton.disabled = false;
                    contactSubmitButton.removeAttribute("aria-busy");
                    contactSubmitButton.textContent =
                        contactSubmitButton.dataset.originalText || "Отправить письмо";
                }
            }
        });
    }

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
        if (form.matches("[data-contact-form]")) {
            return;
        }

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