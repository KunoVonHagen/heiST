import {messageManager, apiClient} from './utils.js';

class AnnouncementsManager {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.isLoading = false;
        this.currentFilters = {
            importance: 'all',
            range: 'all'
        };

        this.initElements();
        this.initEventListeners();
        this.loadAnnouncements();
    }

    initElements() {
        this.listContainer = document.querySelector('.list-container');
        this.emptyState = document.querySelector('.empty-state');
        this.prevPageBtn = document.getElementById('prev-page');
        this.nextPageBtn = document.getElementById('next-page');
        this.pageInfo = document.querySelector('.page-info');
        this.importanceFilter = document.getElementById('importance-filter');
        this.timeRangeFilter = document.getElementById('time-range');
        this.resetFiltersBtn = document.getElementById('reset-filters');
    }

    initEventListeners() {
        this.importanceFilter.addEventListener('change', () => this.updateFilters());
        this.timeRangeFilter.addEventListener('change', () => this.updateFilters());
        this.resetFiltersBtn.addEventListener('click', () => this.resetFilters());
        this.prevPageBtn.addEventListener('click', () => this.prevPage());
        this.nextPageBtn.addEventListener('click', () => this.nextPage());
    }

    async fetchAnnouncements(page = 1) {
        const query = new URLSearchParams({
            page,
            importance: this.currentFilters.importance,
            range: this.currentFilters.range
        });

        try {
            const response = await apiClient.get(`../backend/announcements.php?${query.toString()}`);
            return response?.data || null;
        } catch (error) {
            messageManager.showError('Failed to load announcements');
            console.error('Fetch announcements error:', error);
            return null;
        }
    }

    formatDate(dateString) {
        const options = {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'};
        return new Date(dateString).toLocaleDateString('en-US', options);
    }

    renderAnnouncements(announcements, total) {
        this.listContainer.innerHTML = '';

        if (!announcements || announcements.length === 0) {
            this.emptyState.style.display = 'flex';
            return;
        }

        this.emptyState.style.display = 'none';
        this.totalPages = Math.ceil(total / 10);
        this.updatePaginationButtons();

        const fragment = document.createDocumentFragment();

        announcements.forEach(announcement => {
            const announcementItem = this.createAnnouncementItem(announcement);
            fragment.appendChild(announcementItem);
        });

        this.listContainer.appendChild(fragment);
    }

    createAnnouncementItem(announcement) {
        const announcementItem = document.createElement('div');
        announcementItem.className = `announcement-item ${announcement.importance}`;

        announcementItem.innerHTML = `
      <div class="announcement-header">
        <h3 class="announcement-title">${announcement.title}</h3>
        <span class="announcement-date">${this.formatDate(announcement.date)}</span>
      </div>
      <div class="announcement-content">
        ${announcement.content}
      </div>
      <div class="announcement-meta">
        <span class="announcement-category">${announcement.category}</span>
        <span>Posted by ${announcement.author}</span>
      </div>
    `;

        return announcementItem;
    }

    async loadAnnouncements(page = 1) {
        if (this.isLoading) return;

        this.isLoading = true;
        try {
            const announcementsData = await this.fetchAnnouncements(page);
            if (announcementsData) {
                this.renderAnnouncements(announcementsData.announcements, announcementsData.total);
            }
        } finally {
            this.isLoading = false;
        }
    }

    updateFilters() {
        this.currentFilters = {
            importance: this.importanceFilter.value,
            range: this.timeRangeFilter.value
        };
        this.currentPage = 1;
        this.loadAnnouncements();
    }

    resetFilters() {
        this.importanceFilter.value = 'all';
        this.timeRangeFilter.value = 'all';
        this.updateFilters();
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadAnnouncements(this.currentPage);
        }
    }

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.loadAnnouncements(this.currentPage);
        }
    }

    updatePaginationButtons() {
        this.prevPageBtn.disabled = this.currentPage <= 1;
        this.nextPageBtn.disabled = this.currentPage >= this.totalPages;
        this.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AnnouncementsManager();
});