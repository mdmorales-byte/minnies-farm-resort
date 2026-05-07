const { createApp, ref, computed, onMounted, watch } = Vue;

const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:5000/api'
  : '/api';

createApp({
  setup() {
    const page = ref('home');
    const authTab = ref('login');
    const dashTab = ref('upcoming');

    const authMsg = ref('');
    const authMsgType = ref('');
    const authMsgKey = ref(0);  // For animation re-trigger
    const showRoomModal = ref(false);
    const editingRoom = ref(null);
    const loading = ref(false);
    const serviceAvails = ref([]);
    const showDeleteModal = ref(false);
    const pendingDeleteId = ref(null);
    const showDeleteBookingModal = ref(false);
    const pendingDeleteBookingId = ref(null);
    const showDeleteRoomModal = ref(false);
    const pendingDeleteRoom = ref(null);
    const showServiceAdminModal = ref(false);
    const editingService = ref(null);
    const showDeleteServiceModal = ref(false);
    const pendingDeleteService = ref(null);
    const serviceForm = ref({ name: '', category: 'day_service', price: 0, stock_quantity: -1, description: '', is_active: true });
    const staffTab = ref('bookings');
    const toasts = ref([]);

    // Mobile menu state
    const mobileMenuOpen = ref(false);

    const today = new Date().toISOString().split('T')[0];

    const currentUser = ref(null);
    const token = ref(localStorage.getItem('token') || '');

    const loginForm = ref({ email: '', password: '' });
    const regForm = ref({ name: '', email: '', password: '', confirm: '', role: 'guest' });
    const showLoginPw = ref(false);
    const showRegPw = ref(false);
    const showRegConfirmPw = ref(false);

    const rooms = ref([]);
    const filters = ref({ checkIn: '', checkOut: '', type: '', maxPrice: '', capacity: '' });
    const selectedRoom = ref(null);
    const bookingForm = ref({ checkIn: '', checkOut: '', guests: 1 });
    const roomForm = ref({
      room_number: '', name: '', type: 'Standard', capacity: 2, price_per_night: '',
      description: '', sqm: '', amenities: '', image_url: '', image_url_2: '', image_url_3: '',
      image_url_4: '', image_url_5: '', room_status: 'available'
    });
    const lastBooking = ref({});
    const allBookings = ref([]);
    const services = ref([]);
    const showServiceModal = ref(false);
    const showForgotPassword = ref(false);
    const forgotEmail = ref('');
    const forgotMsg = ref('');
    const forgotMsgType = ref('');
    const showResetPassword = ref(false);
    const resetPassword = ref('');
    const resetPasswordConfirm = ref('');
    const resetMsg = ref('');
    const resetMsgType = ref('');
    const resetToken = ref('');

    // Check URL for reset token on load
    const urlParams = new URLSearchParams(window.location.search);
    const urlResetToken = urlParams.get('reset_token');
    if (urlResetToken) {
      resetToken.value = urlResetToken;
      showResetPassword.value = true;
    }

    // Check URL for verify token on load
    const urlVerifyToken = urlParams.get('verify_token');
    if (urlVerifyToken) {
      fetch(`${API_URL}/auth/verify-email?token=${urlVerifyToken}`)
        .then(res => res.json())
        .then(data => {
          authMsg.value = data.message || data.error;
          authMsgType.value = data.message ? 'success' : 'error';
          page.value = 'auth';
        })
        .catch(err => {
          authMsg.value = 'Connection error: ' + err.message;
          authMsgType.value = 'error';
          page.value = 'auth';
        });
    }

    async function doResetPassword() {
      if (!resetPassword.value || !resetPasswordConfirm.value) return;
      if (resetPassword.value !== resetPasswordConfirm.value) {
        resetMsg.value = 'Passwords do not match.';
        resetMsgType.value = 'error';
        return;
      }
      try {
        const res = await fetch(`${API_URL}/auth/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: resetToken.value, password: resetPassword.value })
        });
        const data = await res.json();
        if (!res.ok) {
          resetMsg.value = data.error || 'Reset failed.';
          resetMsgType.value = 'error';
        } else {
          resetMsg.value = '✅ Password reset successfully! You can now sign in with your new password.';
          resetMsgType.value = 'success';
          showToast('Password updated! Sign in with your new password. 🔐', 'success', 4000);
          setTimeout(() => { showResetPassword.value = false; navigate('auth'); }, 2500);
        }
      } catch (err) {
        resetMsg.value = 'Connection error: ' + err.message;
        resetMsgType.value = 'error';
      }
    }

    async function doForgotPassword() {
      if (!forgotEmail.value) return;
      
      // Validate email format
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(forgotEmail.value)) {
        forgotMsg.value = 'Please enter a valid email address.';
        forgotMsgType.value = 'error';
        return;
      }
      
      try {
        const res = await fetch(`${API_URL}/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: forgotEmail.value })
        });
        const data = await res.json();
        if (!res.ok) {
          forgotMsg.value = data.error || 'Something went wrong.';
          forgotMsgType.value = 'error';
        } else {
          forgotMsg.value = '✅ Password reset link has been sent to your email! Check your inbox.';
          forgotMsgType.value = 'success';
          showToast('Check your email for the reset link! 📧', 'success', 4000);
          forgotEmail.value = '';
          setTimeout(() => { showForgotPassword.value = false; }, 2500);
        }
      } catch (err) {
        forgotMsg.value = 'Connection error: ' + err.message;
        forgotMsgType.value = 'error';
      }
    }
    const serviceModalData = ref({ icon: '', name: '', price: '', guest: '' });

    // ── REVIEWS STATE ──────────────────────────────────────────────────────────
    const reviews = ref([]);
    const reviewsAvg = ref(0);
    const reviewsTotal = ref(0);
    const reviewForm = ref({ rating: 0, review: '' });
    const reviewHover = ref(0);

    // ── COMPUTED ───────────────────────────────────────────────────────────────
    const filteredRooms = computed(() => rooms.value.filter(r => {
      if (filters.value.type && r.type !== filters.value.type) return false;
      if (filters.value.maxPrice && r.price_per_night > Number(filters.value.maxPrice)) return false;
      if (filters.value.capacity && r.capacity < Number(filters.value.capacity)) return false;
      return true;
    }));

    const bookingNights = computed(() => {
      if (!bookingForm.value.checkIn || !bookingForm.value.checkOut) return 0;
      const d = (new Date(bookingForm.value.checkOut) - new Date(bookingForm.value.checkIn)) / 86400000;
      return d > 0 ? d : 0;
    });

    const bookingTotal = computed(() => {
      if (!selectedRoom.value || bookingNights.value <= 0) return 0;
      const sub = selectedRoom.value.price_per_night * bookingNights.value;
      return Math.round(sub + sub * 0.1);
    });

    const upcomingBookings = computed(() =>
      allBookings.value.filter(b => b.guestName === currentUser.value?.name && (b.status === 'confirmed' || b.status === 'pending'))
    );

    const pastBookings = computed(() =>
      allBookings.value.filter(b => b.guestName === currentUser.value?.name && (b.status === 'completed' || b.status === 'cancelled'))
    );

    // Finds a completed booking for the selected room that the current user
    // owns and hasn't reviewed yet — this unlocks the "Leave a Review" form.
    const eligibleBooking = computed(() => {
      if (!currentUser.value || !selectedRoom.value) return null;
      return allBookings.value.find(b =>
        b.user_id === currentUser.value.id &&
        b.room_id === selectedRoom.value.id &&
        b.status === 'completed' &&
        !reviews.value.find(r => r.booking_id === b.id)
      ) || null;
    });

    // ── HELPERS ────────────────────────────────────────────────────────────────
    function statusLabel(status) {
      if (status === 'fully_booked') return 'Fully Booked';
      if (status === 'under_maintenance') return 'Under Maintenance';
      return 'Available';
    }
    function statusClass(status) {
      if (status === 'fully_booked') return 'status-fully-booked';
      if (status === 'under_maintenance') return 'status-maintenance';
      return 'status-confirmed';
    }

    const features = [
      { icon: '🌾', title: 'Nature Escape', desc: 'Immerse yourself in the peaceful sounds of nature and enjoy the fresh air of our beautiful fields.' },
      { icon: '🏡', title: 'Cozy Rooms', desc: 'Farm-inspired rooms with wooden accents, cozy bedding, and garden views.' },
      { icon: '🏐', title: 'Volleyball Games', desc: 'Get active and enjoy some friendly competition on our nature-surrounded volleyball court.' },
      { icon: '📅', title: 'Easy Booking', desc: 'Real-time availability checks and instant confirmation for a hassle-free experience.' },
    ];

    const teamMembers = [
      { name: 'Maximina Cortez Morales', initials: 'MM', role: 'Founder & Owner', photo: 'https://i.imgur.com/WOf3fU3.jpg', desc: 'The heart of the resort. Minnie turned her family farm into a beloved getaway with warmth and determination.', color: 'linear-gradient(135deg,#4a7c3f,#2d4a1e)' },
      { name: 'Mick Daniel Morales', initials: 'MD', role: 'Fullstack Developer', photo: 'https://i.imgur.com/izbkYqi.jpg', desc: "Designed and built the resort's booking interface with Vue.js for a smooth guest experience.", color: 'linear-gradient(135deg,#2d6a5f,#1a2e2a)' },
      { name: 'Kian Antonio', initials: 'KA', role: 'Backend Developer', photo: 'https://i.imgur.com/yiCAiZh.jpg', desc: 'Built the Flask API powering all reservations, authentication, and room management logic.', color: 'linear-gradient(135deg,#c9a84c,#8a6a1a)' },
      { name: 'Curt Aldre Olila', initials: 'CA', role: 'Database Developer', photo: null, desc: 'Designed the MySQL schema ensuring data integrity and fast availability queries.', color: 'linear-gradient(135deg,#5a3a7c,#2d1a4a)' },
    ];

    const faqs = ref([
      { q: 'Do I need to book in advance for day entrance?', a: 'No reservation needed! Just walk in and pay the ₱100 entrance fee at the gate. However, during peak seasons and holidays, we recommend arriving early as capacity may be limited.', open: false },
      { q: 'Can I book the karaoke room on the same day?', a: "Yes! You can walk in and use the karaoke room if it's available. But on weekends and holidays, we highly recommend reserving in advance to secure your slot.", open: false },
      { q: 'Is the entrance fee included when I book a room?', a: "Yes! Guests who book a room at Minnie's Farm Resort enjoy complimentary resort access throughout their stay. The entrance fee only applies to walk-in day guests.", open: false },
      { q: "What are the resort's operating hours?", a: 'The resort is open daily from 7:00 AM to 9:00 PM. Day guests must exit by 8:00 PM. Karaoke sessions must end by 8:30 PM.', open: false },
      { q: 'Can children get a discounted entrance?', a: 'Children aged 3 years old and below enter for FREE. Children 4 to 12 years old pay the regular ₱100 entrance fee.', open: false },
    ]);

    // ── NAVIGATION ─────────────────────────────────────────────────────────────
    function showToast(message, type = 'success', duration = 3000) {
      const toastObj = { message, type, removing: false };
      toasts.value.push(toastObj);
      setTimeout(() => {
        toastObj.removing = true;
        setTimeout(() => {
          toasts.value.splice(toasts.value.indexOf(toastObj), 1);
        }, 300);
      }, duration);
    }

    function navigate(p) {
      page.value = p;
      mobileMenuOpen.value = false; // Close mobile menu on navigation
      authMsg.value = '';
      if (p === 'rooms') { rooms.value = []; setTimeout(fetchRooms, 50); }
      if (p === 'dashboard') {
        if (currentUser.value?.role === 'staff') { fetchAllBookings(); fetchServiceAvails(); }
        else { fetchUserBookings(); fetchServiceAvails(); }
      }
      if (p === 'services') { services.value = []; setTimeout(fetchServices, 50); }
    }

    // ── AUTH ───────────────────────────────────────────────────────────────────
    const GOOGLE_CLIENT_ID = '549203417668-bl1k05ionrenlhnukkui7b6hka24rbbe.apps.googleusercontent.com';

    function googleLogin() {
      if (!window.google || !window.google.accounts) {
        authMsg.value = 'Google services not loaded. Please refresh the page and try again.';
        authMsgType.value = 'error';
        authMsgKey.value++;
        return;
      }
      
      const client = google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile',
        callback: async (tokenResponse) => {
          if (tokenResponse.error) {
            authMsg.value = 'Google login was cancelled.';
            authMsgType.value = 'error';
            authMsgKey.value++;
            return;
          }
          // Get user info from Google
          try {
            const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
              headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
            });
            const googleUser = await res.json();
            
            if (!googleUser.email) {
              authMsg.value = 'Could not get email from Google.';
              authMsgType.value = 'error';
              authMsgKey.value++;
              return;
            }
            
            // Send to our backend
            const backendRes = await fetch(`${API_URL}/auth/google`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email: googleUser.email.toLowerCase(),
                name: googleUser.name,
                google_id: googleUser.sub
              })
            });
            const data = await backendRes.json();
            
            if (!backendRes.ok) { 
              authMsg.value = data.error || 'Google login failed'; 
              authMsgType.value = 'error';
              authMsgKey.value++;
              return; 
            }
            
            token.value = data.token;
            localStorage.setItem('token', data.token);
            currentUser.value = data.user;
            authMsg.value = '✅ Logged in with Google!';
            authMsgType.value = 'success';
            showToast(`Welcome, ${data.user.name}! 🎉`, 'success', 3000);
            setTimeout(() => navigate(data.user.role === 'staff' ? 'dashboard' : 'rooms'), 800);
          } catch (err) {
            authMsg.value = 'Connection error: ' + err.message;
            authMsgType.value = 'error';
            authMsgKey.value++;
          }
        }
      });
      client.requestAccessToken();
    }

    async function doLogin() {
      if (!loginForm.value.email || !loginForm.value.password) {
        authMsg.value = 'Please fill in all fields.';
        authMsgType.value = 'error';
        authMsgKey.value++;
        return;
      }
      
      // Validate email format
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(loginForm.value.email)) {
        authMsg.value = 'Please enter a valid email address.';
        authMsgType.value = 'error';
        authMsgKey.value++;
        return;
      }
      
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: loginForm.value.email, password: loginForm.value.password })
        });
        const data = await res.json();
        if (!res.ok) {
          authMsg.value = data.error || 'Login failed';
          authMsgType.value = 'error';
          authMsgKey.value++;
          return;
        }
        token.value = data.token;
        localStorage.setItem('token', data.token);
        currentUser.value = data.user;
        authMsg.value = '✅ Logged in successfully!';
        authMsgType.value = 'success';
        showToast(`Welcome back, ${data.user.name}! 🎉`, 'success', 3000);
        loginForm.value = { email: '', password: '' };
        setTimeout(() => navigate(data.user.role === 'staff' ? 'dashboard' : 'rooms'), 800);
      } catch (err) {
        authMsg.value = 'Connection error: ' + err.message;
        authMsgType.value = 'error';
        authMsgKey.value++;
      }
      loading.value = false;
    }

    // DEBUG: Auto staff login bypass
    async function debugLogin() {
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/auth/debug-login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (!res.ok) {
          authMsg.value = data.error || 'Debug login failed';
          authMsgType.value = 'error';
          return;
        }
        token.value = data.token;
        localStorage.setItem('token', data.token);
        currentUser.value = data.user;
        authMsg.value = '✅ DEBUG: Logged in as Staff!';
        authMsgType.value = 'success';
        showToast('DEBUG: Staff access granted! 🎉', 'success', 3000);
        setTimeout(() => navigate('dashboard'), 800);
      } catch (err) {
        authMsg.value = 'Debug login error: ' + err.message;
        authMsgType.value = 'error';
      }
      loading.value = false;
    }

    async function doRegister() {
      if (!regForm.value.name || !regForm.value.email || !regForm.value.password) {
        authMsg.value = 'Please fill in all fields.'; 
        authMsgType.value = 'error'; 
        authMsgKey.value++;
        return;
      }
      if (regForm.value.password !== regForm.value.confirm) {
        authMsg.value = 'Passwords do not match.'; 
        authMsgType.value = 'error'; 
        authMsgKey.value++;
        return;
      }
      
      // Validate email format
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(regForm.value.email)) {
        authMsg.value = 'Please enter a valid email address (e.g., user@example.com).'; 
        authMsgType.value = 'error'; 
        authMsgKey.value++;
        return;
      }
      
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: regForm.value.name, email: regForm.value.email, password: regForm.value.password, role: 'guest' })
        });
        const data = await res.json();
        if (!res.ok) { 
          authMsg.value = data.error || 'Registration failed'; 
          authMsgType.value = 'error'; 
          authMsgKey.value++;
          return; 
        }
        // Success: account created, user is verified and can login
        authMsg.value = '✅ Account created! You can now sign in.';
        authMsgType.value = 'success';
        showToast('Account created! Sign in with your credentials. 🎉', 'success', 3000);
        regForm.value = { name: '', email: '', password: '', confirm: '', role: 'guest' };
        // Switch to login tab after 3 seconds
        setTimeout(() => {
          authTab.value = 'login';
          authMsg.value = '';
        }, 3000);
      } catch (err) { 
        authMsg.value = 'Connection error: ' + err.message; 
        authMsgType.value = 'error'; 
        authMsgKey.value++;
      }
      loading.value = false;
    }

    async function logout() {
      try {
        await fetch(`${API_URL}/auth/logout`, { method: 'POST', headers: { 'Authorization': `Bearer ${token.value}` } });
      } catch (err) { console.error('Logout error:', err); }
      currentUser.value = null;
      token.value = '';
      localStorage.removeItem('token');
      navigate('home');
    }

    async function fetchCurrentUser() {
      if (!token.value) return;
      try {
        const res = await fetch(`${API_URL}/auth/me`, { headers: { 'Authorization': `Bearer ${token.value}` } });
        if (res.ok) { const data = await res.json(); currentUser.value = data.user; }
        else { localStorage.removeItem('token'); token.value = ''; }
      } catch (err) { console.error('Fetch user error:', err); }
    }

    // ── ROOMS ──────────────────────────────────────────────────────────────────
    async function fetchRooms() {
      try {
        // Clear existing data first to force UI update
        rooms.value = [];
        // Force Vue to re-render by waiting a tick
        await new Promise(resolve => setTimeout(resolve, 50));
        // Build URL with cache-busting timestamp
        const params = new URLSearchParams();
        params.append('_t', Date.now()); // Cache buster
        if (filters.value.type) params.append('type', filters.value.type);
        if (filters.value.maxPrice) params.append('max_price', filters.value.maxPrice);
        if (filters.value.capacity) params.append('capacity', filters.value.capacity);
        const url = `${API_URL}/rooms?${params.toString()}`;
        const res = await fetch(url, {
          headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        if (res.ok) {
          const data = await res.json();
          rooms.value = [...(data.rooms || [])]; // Force new array reference
          console.log('Rooms fetched:', rooms.value.length, 'rooms');
          rooms.value.forEach(r => {
            if (!r.emoji) {
              const emojis = { 'Standard': '👤', 'Themed': '🎈', 'Deluxe': '👥', 'Suite': '🏠' };
              r.emoji = emojis[r.type] || '🏠';
            }
          });
        }
      } catch (err) { console.error('Fetch rooms error:', err); }
    }

    // ── BOOKINGS ─────────────────────────────────────────
    async function doBook() {
      if (!currentUser.value) { 
        showToast('Please login to book a room! 🔐', 'info');
        navigate('auth'); 
        return; 
      }
      if (bookingNights.value <= 0) {
        showToast('Please select valid dates! 📅', 'error');
        return;
      }
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/bookings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify({ 
            room_id: selectedRoom.value.id, 
            check_in_date: bookingForm.value.checkIn, 
            check_out_date: bookingForm.value.checkOut, 
            num_guests: bookingForm.value.guests,
            total_price: bookingTotal.value,
            user_id: currentUser.value.id
          })
        });
        const data = await res.json();
        if (!res.ok) { 
          showToast(data.error || 'Booking failed', 'error'); 
          return; 
        }
        showToast('Booking successful! 🎉', 'success');
        lastBooking.value = { 
          ref: data.booking.reference_code || 'REF-' + Date.now(), 
          room: selectedRoom.value.name, 
          checkIn: data.booking.check_in_date || bookingForm.value.checkIn, 
          checkOut: data.booking.check_out_date || bookingForm.value.checkOut, 
          guests: data.booking.num_guests || bookingForm.value.guests, 
          total: data.booking.total_price 
        };
        await fetchUserBookings();
        navigate('confirm');
      } catch (err) { 
        showToast('Connection error: ' + err.message, 'error'); 
      }
      loading.value = false;
    }

    async function fetchUserBookings() {
      if (!token.value || !currentUser.value) return;
      try {
        const res = await fetch(`${API_URL}/bookings?user_id=${currentUser.value.id}`, { headers: { 'Authorization': `Bearer ${token.value}` } });
        if (res.ok) {
          const data = await res.json();
          allBookings.value = (data.bookings || []).map(b => ({
            ...b,
            guestName: currentUser.value.name,
            emoji: rooms.value.find(r => r.id === b.room_id)?.emoji || '🏠',
            room: rooms.value.find(r => r.id === b.room_id)?.name || 'Room ' + b.room_id,
            checkIn: b.check_in_date,
            checkOut: b.check_out_date,
            guests: b.num_guests,
            total: b.total_price
          }));
        }
      } catch (err) { console.error('Fetch bookings error:', err); }
    }

    async function fetchAllBookings() {
      try {
        const res = await fetch(`${API_URL}/bookings?staff=true`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        if (res.ok) {
          const data = await res.json();
          // Fetch users and rooms for mapping
          const usersRes = await fetch(`${API_URL}/health`); // Just to check if we can get all info
          
          allBookings.value = (data.bookings || []).map(b => {
            const room = rooms.value.find(r => r.id === b.room_id);
            return {
              ...b, 
              guestName: b.guest_name || 'Guest ' + b.user_id, 
              room: room ? room.name : 'Room ' + b.room_id,
              checkIn: b.check_in_date, 
              checkOut: b.check_out_date,
              guests: b.num_guests, 
              total: b.total_price
            };
          });
        }
      } catch (e) { console.error(e); }
    }

    async function cancelBooking(b) {
      if (!confirm('Cancel this booking?')) return;
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/bookings/${b.id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token.value}` } });
        if (res.ok) await fetchUserBookings();
      } catch (err) { console.error('Cancel booking error:', err); }
      loading.value = false;
    }

    async function updateBookingStatus(b, status) {
      try {
        const t = token.value || localStorage.getItem('token');
        const res = await fetch(`${API_URL}/bookings/${b.id}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${t}` },
          body: JSON.stringify({ status })
        });
        if (res.ok) await fetchAllBookings();
        else { const data = await res.json(); alert(data.error || 'Error updating status'); }
      } catch (e) { alert('Error: ' + e.message); }
    }

    function resetFilters() { filters.value = { checkIn: '', checkOut: '', type: '', maxPrice: '', capacity: '' }; fetchRooms(); }

    // Updated viewRoom — now resets and fetches reviews before navigating
    function viewRoom(room) {
      selectedRoom.value = room;
      bookingForm.value = { checkIn: filters.value.checkIn, checkOut: filters.value.checkOut, guests: 1 };
      // Reset reviews state for the new room
      reviews.value = [];
      reviewsAvg.value = 0;
      reviewsTotal.value = 0;
      reviewForm.value = { rating: 0, review: '' };
      reviewHover.value = 0;
      fetchReviews(room.id);
      navigate('detail');
    }

    // ── REVIEWS ─────────────────────────────────
    async function fetchReviews(roomId) {
      try {
        const res = await fetch(`${API_URL}/reviews?room_id=${roomId}`);
        if (res.ok) {
          const data = await res.json();
          reviews.value = data.reviews || [];
          reviewsAvg.value = data.average_rating || 0;
          reviewsTotal.value = data.total_reviews || 0;
        }
      } catch (err) { console.error('Fetch reviews error:', err); }
    }

    async function submitReview() {
      if (!reviewForm.value.rating) { alert('Please select a star rating.'); return; }
      if (!eligibleBooking.value) return;
      try {
        const res = await fetch(`${API_URL}/reviews`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify({
            room_id: selectedRoom.value.id,
            booking_id: eligibleBooking.value.id,
            rating: reviewForm.value.rating,
            review: reviewForm.value.review,
          })
        });
        const data = await res.json();
        if (!res.ok) { alert(data.error || 'Error submitting review'); return; }
        reviewForm.value = { rating: 0, review: '' };
        reviewHover.value = 0;
        await fetchReviews(selectedRoom.value.id);
      } catch (err) { alert('Connection error: ' + err.message); }
    }

    // ── ROOM MANAGEMENT (staff) ────────────────────────────
    function openAddRoom() {
      editingRoom.value = null;
      roomForm.value = {
        room_number: '', name: '', type: 'Standard', capacity: 2, price_per_night: '',
        description: '', sqm: '', amenities: '', image_url: '', image_url_2: '', image_url_3: '',
        image_url_4: '', image_url_5: '', room_status: 'available'
      };
      showRoomModal.value = true;
    }

    function editRoom(r) {
      editingRoom.value = r;
      roomForm.value = {
        room_number: r.room_number || '', name: r.name, type: r.type, capacity: r.capacity,
        price_per_night: r.price_per_night, description: r.description, sqm: r.sqm || '', amenities: Array.isArray(r.amenities) ? r.amenities.join(', ') : (r.amenities || ''),
        image_url: r.image_url || '',
        image_url_2: r.image_url_2 || '',
        image_url_3: r.image_url_3 || '',
        image_url_4: r.image_url_4 || '',
        image_url_5: r.image_url_5 || '',
        room_status: r.room_status || 'available'
      };
      showRoomModal.value = true;
    }

    async function saveRoom() {
      if (!roomForm.value.room_number || !roomForm.value.name || !roomForm.value.price_per_night) return;
      loading.value = true;
      try {
        const method = editingRoom.value ? 'PUT' : 'POST';
        const url = editingRoom.value ? `${API_URL}/rooms/${editingRoom.value.id}` : `${API_URL}/rooms`;
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify({
            room_number: roomForm.value.room_number,
            name: roomForm.value.name,
            type: roomForm.value.type,
            sqm: roomForm.value.sqm ? Number(roomForm.value.sqm) : null,
            amenities: roomForm.value.amenities ? roomForm.value.amenities.split(',').map(a => a.trim()).filter(a => a) : [],
            capacity: Number(roomForm.value.capacity),
            price_per_night: Number(roomForm.value.price_per_night),
            description: roomForm.value.description,
            image_url: roomForm.value.image_url,
            image_url_2: roomForm.value.image_url_2,
            image_url_3: roomForm.value.image_url_3,
            image_url_4: roomForm.value.image_url_4,
            image_url_5: roomForm.value.image_url_5,
            room_status: roomForm.value.room_status,
          })
        });
        if (res.ok) { 
          const data = await res.json();
          console.log('Room saved response:', data);
          await fetchRooms(); 
          showRoomModal.value = false;
          showToast(editingRoom.value ? 'Room updated! 🏠' : 'Room created! 🏠', 'success');
        }
        else { const data = await res.json(); console.error('Room save error:', data); alert(data.error || 'Error saving room'); }
      } catch (err) { alert('Connection error: ' + err.message); }
      loading.value = false;
    }

    function deleteRoom(r) {
      pendingDeleteRoom.value = r;
      showDeleteRoomModal.value = true;
    }

    async function confirmDeleteRoom() {
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/rooms/${pendingDeleteRoom.value.id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        if (res.ok) await fetchRooms();
        else { const data = await res.json(); console.error(data.error || 'Error deleting room'); }
      } catch (err) { console.error('Connection error: ' + err.message); }
      showDeleteRoomModal.value = false;
      pendingDeleteRoom.value = null;
      loading.value = false;
    }

    function triggerUpload(index) {
      document.getElementById('file-input-' + index).click();
    }

    function removeImage(index) {
      const fieldName = 'image_url' + (index === 1 ? '' : '_' + index);
      roomForm.value[fieldName] = null;
      // Also clear the file input so it can be re-selected
      const input = document.getElementById('file-input-' + index);
      if (input) input.value = '';
      showToast(`Image ${index} removed. Save to apply.`, 'info');
    }

    async function handleFileUpload(event, index) {
      const file = event.target.files[0];
      if (!file) return;

      showToast(`Uploading image ${index}... 📤`, 'info');

      // Use FileReader to send as Base64 (More reliable on Vercel)
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = async () => {
        const base64Data = reader.result;
        try {
          const res = await fetch(`${API_URL}/rooms/upload-image`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token.value}` 
            },
            body: JSON.stringify({ image: base64Data })
          });

          const data = await res.json();
          if (res.ok) {
            const fieldName = 'image_url' + (index === 1 ? '' : '_' + index);
            roomForm.value[fieldName] = data.image_url;
            showToast(`Image ${index} uploaded! 📸`, 'success');
          } else {
            showToast(data.error || 'Upload failed', 'error');
          }
        } catch (err) {
          showToast('Upload error: ' + err.message, 'error');
        }
      };
    }
    async function fetchServices() {
      try {
        const isStaff = (currentUser.value && currentUser.value.role === 'staff') ? 'true' : 'false';
        // Clear existing data first to force UI update
        services.value = [];
        // Force Vue to re-render by waiting a tick
        await new Promise(resolve => setTimeout(resolve, 50));
        // Build URL with cache-busting
        const params = new URLSearchParams();
        params.append('staff', isStaff);
        params.append('_t', Date.now()); // Cache buster
        const url = `${API_URL}/services?${params.toString()}`;
        const res = await fetch(url, {
          headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        if (res.ok) { 
          const data = await res.json(); 
          services.value = [...(data.services || [])]; // Force new array reference
          console.log('Services fetched (Staff: ' + isStaff + '):', services.value.length, 'services');
          console.log('Active services:', services.value.filter(s => s.is_active).length);
        }
      } catch (err) { console.error('Fetch services error:', err); }
    }

    async function fetchServiceAvails() {
      try {
        const res = await fetch(`${API_URL}/services/avails`, {
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        if (res.ok) { const data = await res.json(); serviceAvails.value = data.avails || []; }
      } catch (err) { console.error(err); }
    }

    function deleteServiceAvail(id) {
      pendingDeleteId.value = id;
      showDeleteModal.value = true;
    }

    function deleteBooking(booking) {
      pendingDeleteBookingId.value = booking.id;
      showDeleteBookingModal.value = true;
    }

    async function confirmDelete() {
      try {
        const res = await fetch(`${API_URL}/services/avails/${pendingDeleteId.value}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        if (res.ok) await fetchServiceAvails();
      } catch (err) { console.error(err); }
      showDeleteModal.value = false;
      pendingDeleteId.value = null;
    }

    async function confirmDeleteBooking() {
      try {
        const res = await fetch(`${API_URL}/bookings/${pendingDeleteBookingId.value}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        if (res.ok) await fetchAllBookings();
      } catch (err) { console.error(err); }
      showDeleteBookingModal.value = false;
      pendingDeleteBookingId.value = null;
    }

    async function updateAvailStatus(id, status) {
      try {
        const res = await fetch(`${API_URL}/services/avails/${id}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify({ status })
        });
        const data = await res.json();
        if (res.ok) {
          showToast('Status updated! ', 'success');
          fetchServiceAvails();
        } else {
          showToast(data.error || 'Failed to update status.', 'error');
        }
      } catch (err) {
        showToast('Connection error.', 'error');
      }
    }

    async function updateServiceStock(service) {
      try {
        const res = await fetch(`${API_URL}/services/${service.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token.value}`
          },
          body: JSON.stringify({ stock_quantity: service.stock_quantity })
        });
        const data = await res.json();
        if (res.ok) {
          showToast(`Stock updated for ${service.name}! `, 'success');
        } else {
          showToast(data.error || 'Failed to update stock.', 'error');
        }
      } catch (err) {
        showToast('Connection error.', 'error');
      }
    }

    async function toggleService(service) {
      const newStatus = !service.is_active;
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/services/${service.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token.value}`
          },
          body: JSON.stringify({ is_active: newStatus })
        });
        
        if (res.ok) {
          showToast(`${service.name} is now ${newStatus ? 'Public' : 'Hidden'}!`, 'success');
          await fetchServices(); // Force refresh everything
        } else {
          const data = await res.json();
          showToast(data.error || 'Failed to toggle service.', 'error');
        }
      } catch (err) {
        showToast('Connection error.', 'error');
      }
      loading.value = false;
    }

    function openAddService() {
      editingService.value = null;
      serviceForm.value = { name: '', category: 'day_service', price: 0, stock_quantity: -1, description: '', is_active: true };
      showServiceAdminModal.value = true;
    }

    function editService(s) {
      editingService.value = s;
      serviceForm.value = { ...s };
      showServiceAdminModal.value = true;
    }

    async function saveService() {
      if (!serviceForm.value.name || serviceForm.value.price === '') return;
      loading.value = true;
      try {
        const method = editingService.value ? 'PUT' : 'POST';
        const url = editingService.value ? `${API_URL}/services/${editingService.value.id}` : `${API_URL}/services`;
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify(serviceForm.value)
        });
        if (res.ok) { 
          const data = await res.json();
          console.log('Service saved response:', data);
          await fetchServices(); 
          showServiceAdminModal.value = false;
          showToast(editingService.value ? 'Service updated! ✅' : 'Service created! ✅', 'success');
        } else { 
          const data = await res.json(); 
          console.error('Service save error:', data);
          showToast(data.error || 'Error saving service', 'error'); 
        }
      } catch (err) { showToast('Connection error.', 'error'); }
      loading.value = false;
    }

    function deleteService(s) {
      pendingDeleteService.value = s;
      showDeleteServiceModal.value = true;
    }

    async function confirmDeleteService() {
      loading.value = true;
      try {
        const res = await fetch(`${API_URL}/services/${pendingDeleteService.value.id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        if (res.ok) {
          await fetchServices();
          showToast('Service deleted! 🗑️', 'success');
        } else { 
          const data = await res.json(); 
          showToast(data.error || 'Error deleting service', 'error'); 
        }
      } catch (err) { showToast('Connection error.', 'error'); }
      showDeleteServiceModal.value = false;
      pendingDeleteService.value = null;
      loading.value = false;
    }

    async function availService(name, price) {
      if (!currentUser.value) { navigate('auth'); return; }

      const serviceIds = { 'Day Entrance': 1, 'Karaoke Room': 2, 'Day Fun Bundle': 3 };
      const serviceId = serviceIds[name];

      try {
        const res = await fetch(`${API_URL}/services/${serviceId}/avail`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
          body: JSON.stringify({ notes: `Request from ${currentUser.value.name}` })
        });
        if (!res.ok) { const d = await res.json(); alert(d.error || 'Error'); return; }
      } catch (err) { console.error(err); }

      serviceModalData.value = {
        name, price,
        guest: currentUser.value.name,
        icon: name === 'Karaoke Room' ? '' : name === 'Day Fun Bundle' ? '' : ''
      };
      showServiceModal.value = true;
    }

    // ── MOUNT ──────────
    onMounted(async () => {
      await fetchCurrentUser();
      await fetchRooms();
      if (currentUser.value) {
        if (currentUser.value.role === 'staff') await fetchAllBookings();
        else await fetchUserBookings();
      }
    });

    // ── WATCH staffTab ──────────
    watch(staffTab, (newTab) => {
      if (newTab === 'rooms') { rooms.value = []; fetchRooms(); }
      if (newTab === 'services') { services.value = []; fetchServices(); }
    });

    // ── RETURN (all refs/functions exposed to template) ────────────────────────
    return {
      page, authTab, dashTab, authMsg, authMsgType, authMsgKey, showRoomModal, editingRoom, loading, mobileMenuOpen,
      today, currentUser, token, loginForm, regForm, showLoginPw, showRegPw, showRegConfirmPw, rooms, filters, selectedRoom,
      bookingForm, roomForm, lastBooking, allBookings, features, teamMembers, faqs,
      filteredRooms, bookingNights, bookingTotal, upcomingBookings, pastBookings,
      navigate, doLogin, debugLogin, doRegister, logout, googleLogin, doForgotPassword, doResetPassword,
      showForgotPassword, forgotEmail, forgotMsg, forgotMsgType,
      showResetPassword, resetPassword, resetPasswordConfirm, resetMsg, resetMsgType, resetFilters, fetchRooms, fetchCurrentUser,
      fetchUserBookings, viewRoom, doBook, cancelBooking, openAddRoom, editRoom, saveRoom,
      deleteRoom, confirmDeleteRoom, showDeleteRoomModal, pendingDeleteRoom,
      updateBookingStatus, fetchAllBookings, services, fetchServices,
      statusLabel, statusClass, availService, showServiceModal, serviceModalData,
      serviceAvails, fetchServiceAvails, deleteServiceAvail, confirmDelete,
      showDeleteModal, pendingDeleteId, deleteBooking, confirmDeleteBooking,
      showDeleteBookingModal, pendingDeleteBookingId, updateAvailStatus,
      updateServiceStock,
      toggleService,
      openAddService,
      editService,
      saveService,
      deleteService,
      confirmDeleteService,
      showServiceAdminModal,
      editingService,
      showDeleteServiceModal,
      pendingDeleteService,
      serviceForm,
      triggerUpload,
      removeImage,
      handleFileUpload,
      staffTab,
      navigate,
      showToast,
      // ── reviews ──
      reviews, reviewsAvg, reviewsTotal, reviewForm, reviewHover,
      eligibleBooking, submitReview,
    };
  }
}).mount('#app');

window.addEventListener('error', function(e) { console.error('JavaScript error:', e.error); });
window.addEventListener('unhandledrejection', function(e) { console.error('Unhandled promise rejection:', e.reason); });