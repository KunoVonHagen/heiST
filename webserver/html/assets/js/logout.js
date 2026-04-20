import {apiClient, messageManager} from './utils.js';

class LogoutHandler {
    constructor() {
        this.init();
    }

    init() {
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleLogout();
            });
        }
    }

    async handleLogout() {
        try {
            const confirmLogout = await this.showLogoutConfirmation();
            if (!confirmLogout) return false;

            const result = await apiClient.post('/backend/logout.php');
            if (result === null) return false;

            this.clearClientStorage();
            this.showSuccessAndRedirect();
            return true;
        } catch (error) {
            console.error('Logout error:', error);
            return false;
        }
    }

    clearClientStorage() {
        sessionStorage.clear();
        localStorage.clear();
    }

    showSuccessAndRedirect() {
        messageManager.showSuccess('Logged out successfully');
        setTimeout(() => {
            window.location.href = '/login';
        }, 1000);
    }

    showLogoutConfirmation() {
        return new Promise((resolve) => {
            const dialog = document.createElement('div');
            dialog.className = 'logout-dialog';
            dialog.innerHTML = this.getDialogMarkup();
            document.body.appendChild(dialog);

            this.setupDialogEvents(dialog, resolve);
        });
    }

    getDialogMarkup() {
        return `
            <div class="dialog-content">
                <h3>Confirm Logout</h3>
                <p>Are you sure you want to log out?</p>
                <div class="dialog-buttons">
                    <button class="cancel-btn">Cancel</button>
                    <button class="confirm-btn">Logout</button>
                </div>
            </div>
        `;
    }

    setupDialogEvents(dialog, resolve) {
        dialog.querySelector('.cancel-btn').addEventListener('click', () => {
            this.cleanupDialog(dialog);
            resolve(false);
        });

        dialog.querySelector('.confirm-btn').addEventListener('click', () => {
            this.cleanupDialog(dialog);
            resolve(true);
        });
    }

    cleanupDialog(dialog) {
        if (dialog && dialog.parentNode) {
            document.body.removeChild(dialog);
        }
    }
}


if (typeof window !== 'undefined') {
    new LogoutHandler();
}

export default LogoutHandler;