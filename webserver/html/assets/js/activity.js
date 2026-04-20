import {messageManager, apiClient} from './utils.js';

class ActivityTimeline {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.isLoading = false;
        this.currentFilters = {
            type: 'all',
            range: 'all',
            category: 'all'
        };

        this.initElements();
        this.initEventListeners();
        this.loadActivity();
    }

    initElements() {
        this.timelineContainer = document.querySelector('.timeline-container');
        this.emptyState = document.querySelector('.empty-state');
        this.prevPageBtn = document.getElementById('prev-page');
        this.nextPageBtn = document.getElementById('next-page');
        this.pageInfo = document.querySelector('.page-info');
        this.activityTypeFilter = document.getElementById('activity-type');
        this.timeRangeFilter = document.getElementById('time-range');
        this.categoryFilter = document.getElementById('category-filter');
        this.resetFiltersBtn = document.getElementById('reset-filters');
    }

    initEventListeners() {
        this.activityTypeFilter.addEventListener('change', () => this.updateFilters());
        this.timeRangeFilter.addEventListener('change', () => this.updateFilters());
        this.categoryFilter.addEventListener('change', () => this.updateFilters());
        this.resetFiltersBtn.addEventListener('click', () => this.resetFilters());
        this.prevPageBtn.addEventListener('click', () => this.prevPage());
        this.nextPageBtn.addEventListener('click', () => this.nextPage());
    }

    async fetchActivity(page = 1) {
        const query = new URLSearchParams({
            page,
            type: this.currentFilters.type,
            range: this.currentFilters.range,
            category: this.currentFilters.category
        });

        try {
            const response = await apiClient.get(`../backend/activity.php?${query.toString()}`);
            return response?.data || null;
        } catch (error) {
            messageManager.showError('Failed to load activities');
            console.error('Fetch activity error:', error);
            return null;
        }
    }

    renderActivity(activities, total) {
        this.timelineContainer.innerHTML = '';

        if (!activities || activities.length === 0) {
            this.emptyState.style.display = 'flex';
            return;
        }

        this.emptyState.style.display = 'none';
        this.totalPages = Math.ceil(total / 10);
        this.updatePaginationButtons();

        const fragment = document.createDocumentFragment();

        activities.forEach(activity => {
            const {icon, colorClass} = this.getActivityMetadata(activity);
            const activityItem = this.createActivityItem(activity, icon, colorClass);
            fragment.appendChild(activityItem);
        });

        this.timelineContainer.appendChild(fragment);
    }

    getActivityMetadata(activity) {
        let type = activity.type;
        const metadata = {
            solved: {icon: '✅', colorClass: 'success'},
            failed: {icon: '⚠️', colorClass: 'warning'},
            active: {icon: '⌛', colorClass: 'info'},
            flag_submitted: {icon: '️🏳️', colorClass: 'success'},
            badge: {icon: activity.icon, colorClass: 'gold'},
            default: {icon: '🔍', colorClass: 'neutral'}
        };

        return metadata[type] || metadata.default;
    }

    createActivityItem(activity, icon, colorClass) {
        const activityItem = document.createElement('div');
        activityItem.className = `timeline-item ${activity.type}`;

        const points = activity.points ? `<span class="points ${colorClass}">+${activity.points}pts</span>` : '';
        const challengeLink = activity.item_id ?
            `<a href="${activity.type === 'badge' ? '/badges' : '/challenge'}?id=${activity.item_id}" class="challenge-link">${activity.item_name}</a>` :
            activity.challenge_name || '';
        const badgeInfo = activity.type === 'badge' ? `<div class="badge-info"></div>` : '';
        const categoryBadge = activity.category ?
            `<span class="category-badge ${activity.category.toLowerCase()}">${activity.category}</span>` : '';

        activityItem.innerHTML = `
      <div class="timeline-icon ${colorClass}">${icon}</div>
      <div class="timeline-content">
        <div class="timeline-header">
          <h3>${activity.title}</h3>
          ${points}
        </div>
        <div class="timeline-body">
          ${challengeLink}
          ${badgeInfo}
          ${categoryBadge}
        </div>
        <div class="timeline-footer">
          <time datetime="${activity.timestamp}">${activity.time_ago}</time>
          ${activity.duration ? `<span class="duration">${activity.duration}</span>` : ''}
          ${activity.attempts ? `<span class="attempts">${activity.attempts} attempt${activity.attempts > 1 ? 's' : ''}</span>` : ''}
        </div>
      </div>
    `;

        return activityItem;
    }

    async loadActivity(page = 1) {
        if (this.isLoading) return;

        this.isLoading = true;
        try {
            const activityData = await this.fetchActivity(page);
            if (activityData) {
                this.renderActivity(activityData.activities, activityData.total);
            }
        } finally {
            this.isLoading = false;
        }
    }

    updateFilters() {
        this.currentFilters = {
            type: this.activityTypeFilter.value,
            range: this.timeRangeFilter.value,
            category: this.categoryFilter.value
        };
        this.currentPage = 1;
        this.loadActivity();
    }

    resetFilters() {
        this.activityTypeFilter.value = 'all';
        this.timeRangeFilter.value = 'all';
        this.categoryFilter.value = 'all';
        this.updateFilters();
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadActivity(this.currentPage);
        }
    }

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.loadActivity(this.currentPage);
        }
    }

    updatePaginationButtons() {
        this.prevPageBtn.disabled = this.currentPage <= 1;
        this.nextPageBtn.disabled = this.currentPage >= this.totalPages;
        this.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ActivityTimeline();
});