/**
 * main.js - JavaScript utama untuk CMS Mini
 * Menangani interaksi UI, form validation, dan loading states
 */

document.addEventListener('DOMContentLoaded', function() {
  // Form submission handling dengan loading state
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton) {
        // Tambahkan class loading dan disable button
        submitButton.classList.add('btn-loading');
        submitButton.disabled = true;
        
        // Simpan teks asli button
        if (!submitButton.dataset.originalText) {
          submitButton.dataset.originalText = submitButton.textContent;
        }
      }
      
      // Form validation
      if (!validateForm(form)) {
        e.preventDefault();
        // Kembalikan button ke keadaan semula jika validasi gagal
        if (submitButton) {
          submitButton.classList.remove('btn-loading');
          submitButton.disabled = false;
        }
      }
    });
  });
  
  // Form validation
  function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    // Reset semua error sebelumnya
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    
    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        isValid = false;
        field.classList.add('is-invalid');
        
        // Tambahkan pesan error
        const errorMessage = document.createElement('div');
        errorMessage.className = 'invalid-feedback';
        errorMessage.textContent = `${field.name || 'Field'} tidak boleh kosong`;
        field.parentNode.appendChild(errorMessage);
      }
    });
    
    // Validasi email jika ada
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
      if (field.value && !validateEmail(field.value)) {
        isValid = false;
        field.classList.add('is-invalid');
        
        const errorMessage = document.createElement('div');
        errorMessage.className = 'invalid-feedback';
        errorMessage.textContent = 'Format email tidak valid';
        field.parentNode.appendChild(errorMessage);
      }
    });
    
    return isValid;
  }
  
  function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }
  
  // File input custom styling
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    const fileNameSpan = document.createElement('span');
    fileNameSpan.className = 'file-name';
    fileNameSpan.textContent = 'Tidak ada file dipilih';
    
    input.parentNode.appendChild(fileNameSpan);
    
    input.addEventListener('change', function() {
      if (this.files.length > 0) {
        fileNameSpan.textContent = this.files[0].name;
      } else {
        fileNameSpan.textContent = 'Tidak ada file dipilih';
      }
    });
  });
  
  // Konfirmasi delete
  const deleteButtons = document.querySelectorAll('.btn-delete');
  deleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      if (!confirm('Apakah Anda yakin ingin menghapus item ini?')) {
        e.preventDefault();
      } else {
        // Tambahkan loading state saat konfirmasi delete
        button.classList.add('btn-loading');
        button.disabled = true;
      }
    });
  });
  
  // Keyboard navigation enhancement
  document.addEventListener('keydown', function(e) {
    // Implementasi keyboard shortcuts
    // Alt+N untuk membuat post baru
    if (e.altKey && e.key === 'n') {
      const newPostButton = document.querySelector('.btn-new-post');
      if (newPostButton) {
        e.preventDefault();
        newPostButton.click();
      }
    }
    
    // Escape untuk cancel form
    if (e.key === 'Escape') {
      const cancelButton = document.querySelector('.btn-cancel');
      if (cancelButton) {
        e.preventDefault();
        cancelButton.click();
      }
    }
  });
  
  // Auto-hide flash messages setelah 5 detik
  const flashMessages = document.querySelectorAll('.alert');
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.style.opacity = '0';
      setTimeout(() => {
        message.remove();
      }, 300);
    }, 5000);
  });
});
