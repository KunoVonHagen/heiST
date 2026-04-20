import {messageManager, apiClient} from './utils.js';

class BadgesManager {
    constructor() {
        this.gridContainer = document.querySelector('.grid-container');
        this.emptyState = document.querySelector('.empty-state');
        this.earnedBadgesEl = document.getElementById('earned-badges');
        this.totalBadgesEl = document.getElementById('total-badges');
        this.completionRateEl = document.getElementById('completion-rate');

        this.loadBadges();
    }


    async loadBadges() {
        try {
            const badgesData = await this.fetchBadges();
            if (badgesData) {
                this.renderBadges(badgesData.badges, badgesData.stats);
            }
        } catch (error) {
            this.handleLoadError(error);
        }
    }

    async fetchBadges() {
        try {
            const response = await apiClient.get('../backend/badges.php');
            return response?.data || null;
        } catch (error) {
            console.error('Fetch badges error:', error);
            throw new Error('Failed to load badges');
        }
    }

    renderBadges(badges, stats) {
        this.gridContainer.innerHTML = '';

        if (!badges || badges.length === 0) {
            this.emptyState.style.display = 'flex';
            return;
        }

        this.emptyState.style.display = 'none';
        this.updateStats(stats);

        const fragment = document.createDocumentFragment();
        badges.forEach(badge => {
            const badgeCard = this.createBadgeCard(badge);
            fragment.appendChild(badgeCard);
        });

        this.gridContainer.appendChild(fragment);
    }

    updateStats(stats) {
        this.earnedBadgesEl.textContent = stats.earned;
        this.totalBadgesEl.textContent = stats.total;
        this.completionRateEl.textContent = `${stats.completion_rate}%`;
    }

    createBadgeCard(badge) {
        const badgeCard = document.createElement('div');
        badgeCard.className = `badge-card ${badge.earned ? 'badge-earned' : 'badge-unearned'}`;

        const earnedDate = badge.earned ?
            `<div class="badge-date">Earned: ${this.formatTimeAgo(badge.earned_at)}</div>` :
            '';

        const {progressBar, progressStatus} = this.createProgressElements(badge);

        badgeCard.innerHTML = `
            <div class="badge-header">
                <div class="badge-icon ${badge.rarity}">
                    ${badge.icon || '🏆'}
                </div>
                <h3 class="badge-name">${badge.name}</h3>
                <span class="badge-rarity ${badge.rarity}">${badge.rarity}</span>
            </div>
            <div class="badge-body">
                <p class="badge-description">${badge.description || 'No description available.'}</p>
                <div class="badge-requirements">
                    <strong>Requirements:</strong> ${badge.requirements}
                </div>
            </div>
            <div class="badge-footer">
                <div>
                    ${progressBar}
                    ${progressStatus}
                </div>
                ${earnedDate}
            </div>
        `;

        return badgeCard;
    }

    createProgressElements(badge) {
        let progressBar = '';
        let progressStatus = '';

        if (badge.progress && badge.progress.max > 0) {
            const progressPercent = Math.min(100, Math.round((badge.progress.current / badge.progress.max) * 100));
            progressBar = `
                <div class="badge-progress">
                    <div class="badge-progress-bar ${badge.rarity}" style="width: ${progressPercent}%"></div>
                </div>
            `;
            progressStatus = `<div class="badge-status">${badge.progress.current}/${badge.progress.max} (${progressPercent}%)</div>`;
        } else if (!badge.earned) {
            progressStatus = `<div class="badge-status">Not earned yet</div>`;
        } else {
            progressStatus = `<div class="badge-status">Earned</div>`;
        }

        return {progressBar, progressStatus};
    }

    formatTimeAgo(datetime) {
        if (!datetime) return 'Recently';

        const now = new Date();
        const then = new Date(datetime);
        const diff = Math.floor((now - then) / 1000);

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
        if (diff < 2592000) return `${Math.floor(diff / 604800)}w ago`;
        if (diff < 31536000) return `${Math.floor(diff / 2592000)}mo ago`;
        return `${Math.floor(diff / 31536000)}y ago`;
    }

    handleLoadError(error) {
        messageManager.showError('An error occurred while loading badges');
        console.error('Badges loading error:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new BadgesManager();
});