class ThemeToggle {
    constructor() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.body = document.body;
        this.subscribers = [];
        this.init();
    }

    init() {
        if (!this.themeToggle) return;

        this.loadSavedTheme();
        this.setupEventListeners();
    }

    loadSavedTheme() {
        const savedTheme = localStorage.getItem('theme');
        const isLightTheme = savedTheme === 'light';

        document.documentElement.setAttribute('data-theme', isLightTheme ? 'light' : 'dark');
        this.themeToggle.checked = isLightTheme;
    }

    setupEventListeners() {
        this.themeToggle.addEventListener('change', () => this.handleThemeChange());
    }

    handleThemeChange() {
        const isLightTheme = this.themeToggle.checked;
        const theme = isLightTheme ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        this.subscribers.forEach(callback => callback());
    }

    subscribe(callback) {
        this.subscribers.push(callback);
        return () => {
            this.subscribers = this.subscribers.filter(sub => sub !== callback);
        };
    }
}

const themeToggleInstance = new ThemeToggle();
export default themeToggleInstance;