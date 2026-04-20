import {apiClient, messageManager} from './utils.js';

class ChallengesManager {
    constructor() {
        this.challenges = [];
        this.filteredChallenges = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.challengesPerPage = 10;

        this.leaderboard = {
            currentPage: 1,
            entriesPerPage: 10,
            totalPages: 1,
            currentChallenge: null
        };

        this.domElements = {
            challengesList: document.getElementById('challenges-list'),
            createNewBtn: document.getElementById('create-new-ctf'),
            searchInput: document.getElementById('challenge-search'),
            categoryFilter: document.getElementById('category-filter'),
            statusFilter: document.getElementById('status-filter'),
            prevPageBtn: document.getElementById('prev-page'),
            nextPageBtn: document.getElementById('next-page'),
            leaderboardPrev: document.getElementById('leaderboard-prev'),
            leaderboardNext: document.getElementById('leaderboard-next'),
            pageInfo: document.querySelector('.page-info'),
            editModal: document.getElementById('edit-modal'),
            deleteModal: document.getElementById('delete-modal'),
            leaderboardModal: document.getElementById('leaderboard-modal'),
            editForm: document.getElementById('edit-challenge-form'),
            closeModalBtns: document.querySelectorAll('.close-modal'),
            toggleActive: document.getElementById('edit-active'),
            toggleLabel: document.getElementById('toggle-label'),
            totalChallengesEl: document.getElementById('total-challenges'),
            activeDeploymentsEl: document.getElementById('active-deployments'),
            totalDeploymentsEl: document.getElementById('total-deployments'),
            avgCompletionEl: document.getElementById('avg-completion'),
            confirmSoftDelete: document.getElementById('confirm-soft-delete'),
            confirmHardDelete: document.getElementById('confirm-hard-delete')
        };

        this.loadConfig().then(() => {
            this.init();
        });
    }

    init() {
        this.domElements.editForm.setAttribute('novalidate', '');
        this.setupEventListeners();
        this.fetchChallenges();
    }

    async loadConfig() {
        try {
            const response = await fetch('/config/general.config.json');
            const config = await response.json();
            this.config = config.ctf;
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    setupEventListeners() {
        this.domElements.createNewBtn.addEventListener('click', () => {
            window.location.href = '/create-ctf';
        });

        this.domElements.searchInput.addEventListener('input', () => this.filterChallenges());
        this.domElements.categoryFilter.addEventListener('change', () => this.filterChallenges());
        this.domElements.statusFilter.addEventListener('change', () => this.filterChallenges());

        this.domElements.prevPageBtn.addEventListener('click', () => this.handlePagination('prev'));
        this.domElements.nextPageBtn.addEventListener('click', () => this.handlePagination('next'));

        this.domElements.leaderboardPrev.addEventListener('click', () => this.handleLeaderboardPagination('prev'));
        this.domElements.leaderboardNext.addEventListener('click', () => this.handleLeaderboardPagination('next'));

        this.domElements.closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });

        this.domElements.editForm.addEventListener('submit', (e) => this.handleEditSubmit(e));
        this.domElements.toggleActive.addEventListener('change', () => this.updateToggleLabel());
        this.domElements.confirmSoftDelete.addEventListener('click', () => this.handleSoftDelete());
        this.domElements.confirmHardDelete.addEventListener('click', () => this.handleHardDelete());


        window.addEventListener('click', (e) => {
            if (e.target === this.domElements.editModal) this.closeModals();
            if (e.target === this.domElements.deleteModal) this.closeModals();
            if (e.target === this.domElements.leaderboardModal) this.closeModals();
        });

        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.handleTabSwitch(e));
        });
    }

    async fetchChallenges() {
        try {
            const response = await apiClient.get('../backend/manage-ctf.php?action=get_challenges');

            if (response?.success) {
                this.challenges = response.challenges;
                this.updateStats(response.stats);
                this.filterChallenges();
            }
        } catch (error) {
            console.error('Fetch challenges error:', error);
            messageManager.showError('Failed to load challenges');
        }
    }

    updateStats(stats) {
        this.domElements.totalChallengesEl.textContent = stats.total_challenges;
        this.domElements.activeDeploymentsEl.textContent = stats.active_deployments;
        this.domElements.totalDeploymentsEl.textContent = stats.total_deployments;
        this.domElements.avgCompletionEl.textContent = this.formatCompletionTime(stats.avg_completion_minutes);
    }

    filterChallenges() {
        const searchTerm = this.domElements.searchInput.value.toLowerCase();
        const category = this.domElements.categoryFilter.value;
        const status = this.domElements.statusFilter.value;

        this.filteredChallenges = this.challenges.filter(challenge => {
            const matchesSearch =
                challenge.name.toLowerCase().includes(searchTerm) ||
                challenge.description.toLowerCase().includes(searchTerm);
            const matchesCategory = category === '' || challenge.category === category;
            const matchesStatus = status === '' ||
                (status === 'active' && challenge.is_active) ||
                (status === 'inactive' && !challenge.is_active);

            return matchesSearch && matchesCategory && matchesStatus;
        });

        this.currentPage = 1;
        this.displayChallenges();
    }

    displayChallenges() {
        const startIdx = (this.currentPage - 1) * this.challengesPerPage;
        const endIdx = startIdx + this.challengesPerPage;
        const paginatedChallenges = this.filteredChallenges.slice(startIdx, endIdx);

        this.domElements.challengesList.innerHTML = paginatedChallenges.length === 0
            ? this.createNoResultsRow()
            : paginatedChallenges.map(challenge => this.createChallengeRow(challenge)).join('');

        if (paginatedChallenges.length > 0) {
            paginatedChallenges.forEach(challenge => {
                const row = this.domElements.challengesList.querySelector(`tr button[data-id="${challenge.id}"]`)?.closest('tr');
                if (row) {
                    row.querySelector('.edit').addEventListener('click', () => this.openEditModal(challenge));
                    row.querySelector('.delete').addEventListener('click', () => this.openDeleteModal(challenge));
                    row.querySelector('.leaderboard').addEventListener('click', () => {this.openLeaderboardModal(challenge)});
                }
            });
        }

        this.updatePagination();
    }

    createNoResultsRow() {
        return '<tr><td colspan="8" class="no-results">No challenges found. Create your first challenge!</td></tr>';
    }

    createChallengeRow(challenge) {
        return `
            <tr>
                <td>
                    <div class="challenge-info">
                        <img src="${challenge.image_path || '../assets/images/ctf-default.png'}" 
                             alt="${challenge.name}" class="challenge-image">
                        <div>
                            <div class="challenge-name">
                                <a href="/challenge?id=${challenge.id}" target="_blank">
                                    ${challenge.name}
                                </a>
                            </div>
                        </div>
                    </div>
                </td>
                <td><span class="category-badge">${this.formatCategory(challenge.category)}</span></td>
                <td><span class="difficulty-badge difficulty-${challenge.difficulty}">
                    ${this.formatDifficulty(challenge.difficulty)}
                </span></td>
                <td><span class="status-badge ${challenge.is_active ? 'status-active' : 'status-inactive'}">
                    ${challenge.is_active ? 'Active' : 'Inactive'}
                </span></td>
                <td>${challenge.total_deployments}</td>
                <td>${challenge.active_deployments}</td>
                <td>${this.formatCompletionTime(challenge.avg_completion_minutes)}</td>
                <td>
                    <div class="actions-cell">
                    <button class="action-btn edit" data-id="${challenge.id}">
                        <i class="fa-solid fa-edit"></i>
                    </button>
                    <button class="action-btn delete" data-id="${challenge.id}">
                        <i class="fa-solid ${challenge.marked_for_deletion ? 'fa-rotate-left' : 'fa-trash'}"></i>
                    </button>
                    <button class="action-btn leaderboard view-toggle-button">
                        <span class="stripe"></span>
                        <span class="stripe"></span>
                        <span class="stripe"></span>
                    </button>
                    </div>
                </td>
            </tr>
        `;
    }

    handlePagination(direction) {
        const newPage = direction === 'prev' ? this.currentPage - 1 : this.currentPage + 1;
        this.totalPages = Math.ceil(this.filteredChallenges.length / this.challengesPerPage);

        if (newPage > 0 && newPage <= this.totalPages) {
            this.currentPage = newPage;
            this.displayChallenges();
        }
    }

    updatePagination() {
        this.totalPages = Math.ceil(this.filteredChallenges.length / this.challengesPerPage);
        this.domElements.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages || 1}`;
        this.domElements.prevPageBtn.disabled = this.currentPage <= 1;
        this.domElements.nextPageBtn.disabled = this.currentPage >= this.totalPages || this.totalPages === 0;
    }

    openEditModal(challenge) {
        document.getElementById('edit-challenge-id').value = challenge.id;
        document.getElementById('edit-name').value = challenge.name;
        document.getElementById('edit-description').value = challenge.description;
        document.getElementById('edit-category').value = challenge.category;
        document.getElementById('edit-difficulty').value = challenge.difficulty;
        document.getElementById('edit-hint').value = challenge.hint || '';
        document.getElementById('edit-solution').value = challenge.solution || '';
        this.domElements.toggleActive.checked = challenge.is_active;
        this.updateToggleLabel();
        this.domElements.editModal.classList.add('show');
    }

    openDeleteModal(challenge) {
        document.getElementById('delete-challenge-id').value = challenge.id;

        const modal = this.domElements.deleteModal;
        const modalHeader = modal.querySelector('.modal-header h2');
        const softDeleteTab = modal.querySelector('.tab-button[data-tab="soft-delete"]');
        const softDeleteContent = modal.querySelector('#soft-delete-tab');
        const softDeleteBtn = modal.querySelector('#confirm-soft-delete');

        if (challenge.marked_for_deletion) {
            modalHeader.textContent = 'Challenge Recovery';
            softDeleteTab.textContent = 'Restore Challenge';
            softDeleteContent.querySelector('h4').textContent = 'Restore Challenge';
            softDeleteContent.querySelector('p').textContent = 'Return this challenge to active status.';
            softDeleteContent.querySelector('ul').innerHTML = `
            <li>Challenge will be available immediately</li>
            <li>All existing instances remain unaffected</li>
            <li>Can be deleted again if needed</li>
        `;
            softDeleteBtn.innerHTML = '<i class="fa-solid fa-rotate-left"></i> Restore Challenge';
            softDeleteBtn.classList.replace('button-warning', 'button-success');
        } else {
            modalHeader.textContent = 'Delete Challenge';
            softDeleteTab.textContent = 'Standard Delete';
            softDeleteContent.querySelector('h4').textContent = 'Standard (Safe) Deletion';
            softDeleteContent.querySelector('p').textContent = 'The challenge will be marked for deletion and automatically removed when all active instances are terminated.';
            softDeleteContent.querySelector('ul').innerHTML = `
            <li>Active instances can finish their sessions</li>
            <li>Challenge remains available until last instance closes</li>
            <li>Can be undone while instances are running</li>
        `;
            softDeleteBtn.innerHTML = '<i class="fa-solid fa-trash-alt"></i> Mark for Deletion';
            softDeleteBtn.classList.replace('button-success', 'button-warning');
        }

        modal.classList.add('show');
    }

    openLeaderboardModal(challenge) {
        const leaderboardChallengeImage = document.getElementById('leaderboard-challenge-image');
        const leaderboardChallengeCategory = document.getElementById('leaderboard-challenge-category')
        const leaderboardChallengeDifficulty = document.getElementById('leaderboard-challenge-difficulty');

        document.getElementById('leaderboard-challenge-name').textContent = challenge.name;

        this.leaderboard.currentChallenge = challenge;
        this.leaderboard.currentPage = 1;

        leaderboardChallengeImage.src = challenge.image_path || '../assets/images/ctf-default.png';
        leaderboardChallengeImage.alt = challenge.name;

        leaderboardChallengeCategory.textContent = this.formatCategory(challenge.category);
        leaderboardChallengeCategory.className = 'category-badge';

        leaderboardChallengeDifficulty.textContent = this.formatDifficulty(challenge.difficulty);
        leaderboardChallengeDifficulty.className = `difficulty-badge difficulty-${challenge.difficulty}`;

        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';
        this.domElements.leaderboardModal.style.overflow = 'auto';

        this.domElements.leaderboardModal.classList.add('show');
        this.fetchLeaderboard();
    }

    async fetchLeaderboard() {
        if (!this.leaderboard.currentChallenge) return;

        try {
            const response = await apiClient.get(`../backend/manage-ctf.php?action=get_leaderboard&id=${this.leaderboard.currentChallenge.id}&page=${this.leaderboard.currentPage}&limit=${this.leaderboard.entriesPerPage}`);

            if (response?.success) {
                this.displayLeaderboard(response.leaderboard, response.total_entries);
            }
        } catch (error) {
            console.error('Fetch leaderboard error:', error);
            messageManager.showError('Failed to load leaderboard');
        }
    }

    displayLeaderboard(entries, totalEntries) {
        document.getElementById('leaderboard-page-info').textContent = `Page ${this.leaderboard.currentPage} of ${this.leaderboard.totalPages || 1}`;
        const leaderboardEntries = document.getElementById('leaderboard-entries');

        this.leaderboard.totalPages = Math.ceil(totalEntries / this.leaderboard.entriesPerPage);
        this.domElements.leaderboardPrev.disabled = this.leaderboard.currentPage <= 1;
        this.domElements.leaderboardNext.disabled = this.leaderboard.currentPage >= this.leaderboard.totalPages || this.leaderboard.totalPages === 0;

        leaderboardEntries.innerHTML = '';

        if (entries.length === 0) {
            leaderboardEntries.innerHTML = `
                <tr>
                    <td colspan="4" class="no-results">No leaderboard entries yet</td>
                </tr>
            `;
            return;
        }

        leaderboardEntries.innerHTML = entries.map(entry => this.createLeaderboardEntry(entry)).join('');
    }
    createLeaderboardEntry(entry) {
        const timeFormatted = this.formatLeaderboardTime(entry.total_seconds);
        const username = this.escapeHtml(entry.username);
        const profileUrl = `/profile/${encodeURIComponent(username)}`;

        return `
        <tr>
            <td class="leaderboard-rank">#${entry.rank}</td>
            <td>
                <div class="leaderboard-user">
                    <img src="${entry.avatar_url || '../assets/images/default-avatar.png'}" 
                         alt="${username}" class="leaderboard-avatar">
                    <a href="${profileUrl}" class="leaderboard-username">${username}</a>
                </div>
            </td>
            <td class="leaderboard-points">${entry.total_points}</td>
            <td class="leaderboard-time">${timeFormatted}</td>
        </tr>
    `;
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    formatLeaderboardTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            secs.toString().padStart(2, '0')
        ].join(':');
    }

    handleLeaderboardPagination(direction) {
        const newPage = direction === 'prev'
            ? this.leaderboard.currentPage - 1
            : this.leaderboard.currentPage + 1;

        if (newPage > 0 && newPage <= this.leaderboard.totalPages) {
            this.leaderboard.currentPage = newPage;
            this.fetchLeaderboard();
        }
    }

    closeModals() {
        this.domElements.editModal.classList.remove('show');
        this.domElements.deleteModal.classList.remove('show');
        this.domElements.leaderboardModal.classList.remove('show');

        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';
        this.domElements.leaderboardModal.style.overflowY = '';
    }

    updateToggleLabel() {
        this.domElements.toggleLabel.textContent = this.domElements.toggleActive.checked ? 'Active' : 'Inactive';
    }

    async handleEditSubmit(e) {
        e.preventDefault();

        if (!this.validateChallengeForm()) return;

        const formData = new FormData();
        formData.append('action', 'update_challenge');
        formData.append('id', document.getElementById('edit-challenge-id').value);
        formData.append('name', document.getElementById('edit-name').value.trim());
        formData.append('description', document.getElementById('edit-description').value.trim());
        formData.append('category', document.getElementById('edit-category').value);
        formData.append('difficulty', document.getElementById('edit-difficulty').value);
        formData.append('hint', document.getElementById('edit-hint').value.trim());
        formData.append('solution', document.getElementById('edit-solution').value.trim());
        formData.append('isActive', this.domElements.toggleActive.checked);

        try {
            const response = await apiClient.post('../backend/manage-ctf.php', formData);

            if (response?.success) {
                messageManager.showSuccess('Challenge updated successfully!');
                this.closeModals();
                this.fetchChallenges();
            }
        } catch (error) {
            console.error('Edit challenge error:', error);
            messageManager.showError('Failed to update challenge');
        }
    }

    async handleSoftDelete() {
        const challengeId = document.getElementById('delete-challenge-id').value;
        const challenge = this.challenges.find(c => c.id === Number(challengeId));

        try {
            let response;
            if (challenge.marked_for_deletion) {
                const formData = new FormData();
                formData.append('action', 'restore_challenge');
                formData.append('id', challengeId);
                response = await apiClient.post('../backend/manage-ctf.php', formData);
            } else {
                response = await apiClient.delete('../backend/manage-ctf.php', {
                    data: {
                        action: 'delete_challenge',
                        id: challengeId,
                        force: false
                    }
                });
            }

            if (response?.success) {
                messageManager.showSuccess(response.message);
                this.closeModals();
                this.fetchChallenges();
            }
        } catch (error) {
            console.error('Soft delete/restore error:', error);
            messageManager.showError(challenge.marked_for_deletion
                ? 'Failed to restore challenge'
                : 'Failed to deactivate challenge');
        }
    }

    async handleHardDelete() {
        const confirmed = await this.showConfirmationDialog(
            'WARNING: This will immediately terminate all active instances and permanently delete the challenge. Are you absolutely sure?'
        );

        if (!confirmed) return;

        const challengeId = document.getElementById('delete-challenge-id').value;

        try {
            const response = await apiClient.delete('../backend/manage-ctf.php', {
                data: {
                    action: 'delete_challenge',
                    id: challengeId,
                    force: true
                }
            });

            if (response?.success) {
                messageManager.showSuccess('Challenge and all instances deleted');
                this.closeModals();
                this.fetchChallenges();
            }
        } catch (error) {
            console.error('Hard delete error:', error);
            messageManager.showError('Failed to delete challenge');
        }
    }

    validateChallengeForm() {
        const errors = [];
        const fields = [];

        const name = document.getElementById('edit-name').value.trim();
        const description = document.getElementById('edit-description').value.trim();
        const category = document.getElementById('edit-category').value;
        const difficulty = document.getElementById('edit-difficulty').value;
        const hint = document.getElementById('edit-hint').value.trim();
        const solution = document.getElementById('edit-solution').value.trim();
        const challengeId = document.getElementById('edit-challenge-id').value;
        const challenge = this.challenges.find(c => c.id === Number(challengeId));
        const isActive = this.domElements.toggleActive.checked;

        if (!name) {
            errors.push('Challenge name is required');
            fields.push('edit-name');
        } else if (name.length > this.config.MAX_CTF_NAME_LENGTH) {
            errors.push(`Name cannot exceed ${this.config.MAX_CTF_NAME_LENGTH} characters`);
            fields.push('edit-name');
        }

        if (!description) {
            errors.push('Description is required');
            fields.push('edit-description');
        } else if (description.length > this.config.MAX_CTF_DESCRIPTION_LENGTH) {
            errors.push(`Description cannot exceed ${this.config.MAX_CTF_DESCRIPTION_LENGTH} characters`);
            fields.push('edit-description');
        }

        if (!category) {
            errors.push('Category is required');
            fields.push('edit-category');
        }

        if (!['easy', 'medium', 'hard'].includes(difficulty)) {
            errors.push('Please select a valid difficulty level');
            fields.push('edit-difficulty');
        }

        if (hint.length > this.config.MAX_HINT_LENGTH) {
            errors.push(`Hint cannot exceed ${this.config.MAX_HINT_LENGTH} characters`);
            fields.push('edit-hint');
        }

        if (solution.length > this.config.MAX_SOLUTION_LENGTH) {
            errors.push(`Solution cannot exceed ${this.config.MAX_SOLUTION_LENGTH} characters`);
            fields.push('edit-solution');
        }

        if (challenge?.marked_for_deletion && isActive) {
            errors.push('Cannot activate a challenge marked for deletion. Restore it first.');
            fields.push('edit-active');
        }

        if (errors.length) {
            this.highlightErrorFields(fields);
            if (fields.includes('edit-active')) {
                this.domElements.toggleActive.checked = false;
                this.updateToggleLabel();
            }

            messageManager.showError(errors.join('<br>'));
            return false;
        }

        return true;
    }

    highlightErrorFields(fieldIds) {
        fieldIds.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.classList.add('error-field');
                field.addEventListener('input', () => {
                    field.classList.remove('error-field');
                }, {once: true});
            }
        });
    }

    formatCompletionTime(minutes) {
        if (!minutes || minutes <= 0) return 'N/A';

        const hours = Math.floor(minutes / 60);
        const mins = Math.floor(minutes % 60);
        return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    }

    formatCategory(category) {
        const categories = {
            'web': 'Web',
            'crypto': 'Cryptography',
            'forensics': 'Forensics',
            'reverse': 'Reverse Engineering',
            'pwn': 'Binary Exploitation',
            'misc': 'Miscellaneous'
        };
        return categories[category] || category;
    }

    formatDifficulty(difficulty) {
        return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
    }

    handleTabSwitch(e) {
        const button = e.currentTarget;
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        const tabId = button.dataset.tab + '-tab';
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabId).classList.add('active');
    }

    async showConfirmationDialog(message) {
        return new Promise(resolve => {
            resolve(confirm(message));
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChallengesManager();
});