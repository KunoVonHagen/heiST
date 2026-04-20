import {apiClient, messageManager} from './utils.js';

class AnnouncementsManager {
    constructor() {
        this.announcements = [];
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.totalPages = 1;
        this.config = null;

        this.domElements = {
            announcementsList: document.getElementById('announcements-list'),
            createBtn: document.getElementById('create-announcement'),
            prevPageBtn: document.getElementById('prev-page'),
            nextPageBtn: document.getElementById('next-page'),
            pageInfo: document.querySelector('.page-info'),
            editorModal: document.getElementById('editor-modal'),
            deleteModal: document.getElementById('delete-modal'),
            announcementForm: document.getElementById('announcement-form'),
            deleteBtn: document.getElementById('confirm-delete'),
            closeModalBtns: document.querySelectorAll('.close-modal'),
            modalTitle: document.getElementById('modal-title')
        };
        this.loadConfig().then(() => {
            this.init();
        });
    }

    init() {
        this.domElements.announcementForm.setAttribute('novalidate', '');
        this.setupEventListeners();
        this.fetchAnnouncements();
    }

    async loadConfig() {
        try {
            const response = await fetch('/config/general.config.json');
            const config = await response.json();
            this.config = config.announcement;
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    setupEventListeners() {
        this.domElements.createBtn.addEventListener('click', () => this.openEditor());
        this.domElements.prevPageBtn.addEventListener('click', () => this.handlePagination('prev'));
        this.domElements.nextPageBtn.addEventListener('click', () => this.handlePagination('next'));
        this.domElements.announcementForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.domElements.deleteBtn.addEventListener('click', () => this.handleDelete());

        this.domElements.closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });

        window.addEventListener('click', (e) => {
            if (e.target === this.domElements.editorModal) this.domElements.editorModal.classList.remove('show');
            if (e.target === this.domElements.deleteModal) this.domElements.deleteModal.classList.remove('show');
        });
    }

    async fetchAnnouncements(page = 1) {
        try {
            const response = await apiClient.get(`../backend/manage-announcements.php?action=list&page=${page}`);

            if (response?.success) {
                this.announcements = response.data.announcements;
                this.totalPages = Math.ceil(response.data.total / this.itemsPerPage);
                this.currentPage = page;
                this.renderAnnouncements();
                this.updatePagination();
            }
        } catch (error) {
            console.error('Fetch announcements error:', error);
            messageManager.showError('Failed to load announcements');
        }
    }

    formatDate(dateString) {
        const options = {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'};
        return new Date(dateString).toLocaleDateString('en-US', options);
    }

    renderAnnouncements() {
        this.domElements.announcementsList.innerHTML = this.announcements.length === 0
            ? this.createNoAnnouncementsRow()
            : this.announcements.map(announcement => this.createAnnouncementRow(announcement)).join('');


        if (this.announcements.length > 0) {
            this.announcements.forEach(announcement => {
                const row = this.domElements.announcementsList.querySelector(`tr button[data-id="${announcement.id}"]`)?.closest('tr');
                if (row) {
                    row.querySelector('.edit').addEventListener('click', () => this.openEditor(announcement));
                    row.querySelector('.delete').addEventListener('click', () => this.openDeleteModal(announcement.id));
                }
            });
        }
    }

    createNoAnnouncementsRow() {
        return '<tr><td colspan="6" class="no-announcements">No announcements found</td></tr>';
    }

    createAnnouncementRow(announcement) {
        return `
            <tr>
                <td>${announcement.title}</td>
                <td>${announcement.category}</td>
                <td>
                    <span class="importance-badge badge-${announcement.importance}">
                        ${announcement.importance.charAt(0).toUpperCase() + announcement.importance.slice(1)}
                    </span>
                </td>
                <td>${this.formatDate(announcement.created_at)}</td>
                <td>${this.formatDate(announcement.updated_at)}</td>
                <td class="actions-cell">
                    <button class="action-btn edit" data-id="${announcement.id}">
                        <i class="fa-solid fa-edit"></i>
                    </button>
                    <button class="action-btn delete" data-id="${announcement.id}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }

    updatePagination() {
        this.domElements.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages || 1}`;
        this.domElements.prevPageBtn.disabled = this.currentPage <= 1;
        this.domElements.nextPageBtn.disabled = this.currentPage >= this.totalPages;
    }

    handlePagination(direction) {
        const newPage = direction === 'prev' ? this.currentPage - 1 : this.currentPage + 1;
        if (newPage > 0 && newPage <= this.totalPages) {
            this.fetchAnnouncements(newPage);
        }
    }

    openEditor(announcement = null) {
        if (announcement) {
            this.domElements.modalTitle.textContent = 'Edit Announcement';
            document.getElementById('announcement-id').value = announcement.id;
            document.getElementById('announcement-title').value = announcement.title;
            document.getElementById('announcement-short-desc').value = announcement.short_description || '';
            document.getElementById('announcement-content').value = announcement.content;
            document.getElementById('announcement-category').value = announcement.category;
            document.getElementById('announcement-importance').value = announcement.importance;
        } else {
            this.domElements.modalTitle.textContent = 'Create New Announcement';
            this.domElements.announcementForm.reset();
            document.getElementById('announcement-id').value = '';
        }

        this.domElements.editorModal.classList.add('show');
    }

    openDeleteModal(id) {
        document.getElementById('delete-announcement-id').value = id;
        this.domElements.deleteModal.classList.add('show');
    }

    closeModals() {
        this.domElements.editorModal.classList.remove('show');
        this.domElements.deleteModal.classList.remove('show');
    }

    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.validateAnnouncementForm()) return;

        const id = document.getElementById('announcement-id').value;
        const isEdit = !!id;
        const formData = this.getFormData();

        try {
            const response = await apiClient.post(
                `../backend/manage-announcements.php?action=${isEdit ? 'update' : 'create'}`,
                isEdit ? {id, ...formData} : formData
            );

            if (response?.success) {
                messageManager.showSuccess(`Announcement ${isEdit ? 'updated' : 'created'} successfully!`);
                this.closeModals();
                this.fetchAnnouncements(this.currentPage);
            }
        } catch (error) {
            console.error('Form submission error:', error);
            messageManager.showError('Failed to save announcement');
        }
    }

    getFormData() {
        return {
            title: document.getElementById('announcement-title').value.trim(),
            short_description: document.getElementById('announcement-short-desc').value.trim(),
            content: document.getElementById('announcement-content').value.trim(),
            category: document.getElementById('announcement-category').value,
            importance: document.getElementById('announcement-importance').value
        };
    }

    async handleDelete() {
        const id = document.getElementById('delete-announcement-id').value;

        try {
            const response = await apiClient.post('../backend/manage-announcements.php?action=delete', {id});

            if (response?.success) {
                messageManager.showSuccess('Announcement deleted successfully!');
                this.closeModals();
                this.fetchAnnouncements(this.currentPage);
            }
        } catch (error) {
            console.error('Delete error:', error);
            messageManager.showError('Failed to delete announcement');
        }
    }

    validateAnnouncementForm() {
        const errors = [];
        const fields = [];
        const formData = this.getFormData();

        if (!formData.title) {
            errors.push('Title is required');
            fields.push('announcement-title');
        } else if (formData.title.length > this.config.MAX_ANNOUNCEMENT_NAME_LENGTH) {
            errors.push(`Title cannot exceed ${this.config.MAX_ANNOUNCEMENT_NAME_LENGTH} characters`);
            fields.push('announcement-title');
        }

        if (formData.short_description.length > this.config.MAX_ANNOUNCEMENT_SHORT_DESCRIPTION_LENGTH) {
            errors.push(`Short description cannot exceed ${this.config.MAX_ANNOUNCEMENT_SHORT_DESCRIPTION_LENGTH} characters`);
            fields.push('announcement-short-desc');
        }

        if (!formData.content) {
            errors.push('Content is required');
            fields.push('announcement-content');
        } else if (formData.content.length > this.config.MAX_ANNOUNCEMENT_DESCRIPTION_LENGTH) {
            errors.push(`Content cannot exceed ${this.config.MAX_ANNOUNCEMENT_DESCRIPTION_LENGTH} characters`);
            fields.push('announcement-content');
        }

        if (!['general', 'updates', 'maintenance', 'events', 'security'].includes(formData.category)) {
            errors.push('Category is required');
            fields.push('announcement-category');
        }

        if (!['normal', 'important', 'critical'].includes(formData.importance)) {
            errors.push('Please select a valid importance level');
            fields.push('announcement-importance');
        }

        if (errors.length) {
            this.highlightErrorFields(fields);
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
}

document.addEventListener('DOMContentLoaded', () => {
    new AnnouncementsManager();
});