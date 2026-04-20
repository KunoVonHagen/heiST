class DropdownMenu {
    constructor(element) {
        this.element = element;
        this.toggle = element.querySelector('.dropdown-toggle');
        this.menu = element.querySelector('.dropdown-menu');
        this.currentPath = window.location.pathname;
        this.observer = null;

        this.init();
    }

    init() {
        this.setupMutationObserver();
        this.setupToggle();
        this.setupOutsideClick();
        this.setupBaseKeyboardNavigation();
        this.markActiveItems();
    }

    setupMutationObserver() {
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                if (mutation.type === 'childList') {
                    this.items = this.menu.querySelectorAll('.dropdown-item');
                    this.setupItemEventListeners();
                    this.markActiveItems();
                }
            });
        });

        this.observer.observe(this.menu, {
            childList: true,
            subtree: true
        });
    }

    setupToggle() {
        this.toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = this.toggle.getAttribute('aria-expanded') === 'true';
            this.toggle.setAttribute('aria-expanded', String(!isOpen));


            if (!isOpen && this.items && this.items.length > 0) {
                setTimeout(() => this.items[0].focus(), 0);
            }
        });
    }

    setupOutsideClick() {
        document.addEventListener('click', () => {
            this.toggle.setAttribute('aria-expanded', 'false');
        });
    }

    setupBaseKeyboardNavigation() {
        this.menu.addEventListener('keydown', (e) => {
            if (!this.items || this.items.length === 0) return;

            const currentItem = document.activeElement;
            const currentIndex = Array.from(this.items).indexOf(currentItem);

            switch (e.key) {
                case 'Escape':
                    this.closeMenu();
                    break;
                case 'ArrowDown':
                    this.focusNextItem(e, currentIndex);
                    break;
                case 'ArrowUp':
                    this.focusPreviousItem(e, currentIndex);
                    break;
            }
        });
    }

    setupItemEventListeners() {
        this.items.forEach(item => {
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    item.click();
                }
            });
        });
    }

    closeMenu() {
        this.toggle.setAttribute('aria-expanded', 'false');
        this.toggle.focus();
    }

    focusNextItem(e, currentIndex) {
        e.preventDefault();
        const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % this.items.length;
        this.items[nextIndex].focus();
    }

    focusPreviousItem(e, currentIndex) {
        e.preventDefault();
        const prevIndex = currentIndex <= 0 ? this.items.length - 1 : currentIndex - 1;
        this.items[prevIndex].focus();
    }

    markActiveItems() {
        if (!this.items) return;

        this.items.forEach(item => {
            item.classList.remove('active');
            const href = item.getAttribute('href');
            if (href && this.currentPath.startsWith(href)) {
                item.classList.add('active');
            }
        });
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }

    }
}


document.addEventListener('DOMContentLoaded', () => {
    const dropdownElements = document.querySelectorAll('.dropdown.menu');
    dropdownElements.forEach(element => {
        new DropdownMenu(element);
    });
});