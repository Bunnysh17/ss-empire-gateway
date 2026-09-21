// SS EMPIRE - Background Video Sound Controller
// Controls the audio directly from the background video in 1:1 hardware sync
// Featuring spinning Suyash logo, Mute/Unmute toggle, and Volume adjustment (+ / - & Slider)

(function() {
  const DEFAULT_VOL = 0.6;
  let video = null;
  let isMuted = true;
  let savedVol = parseFloat(localStorage.getItem('ssempire_video_vol'));
  if (isNaN(savedVol) || savedVol === null) {
    savedVol = DEFAULT_VOL;
  }
  let userPrefMuted = localStorage.getItem('ssempire_video_muted');
  // Default to unmuted on user preference unless explicitly muted by user
  let wantsSound = userPrefMuted !== 'true';

  function getVideoElement() {
    return document.getElementById('bgVideo') || document.querySelector('video.video-bg') || document.querySelector('video');
  }

  function initController() {
    if (document.getElementById('bgmWidget')) return;
    video = getVideoElement();
    if (!video) {
      setTimeout(initController, 250);
      return;
    }

    // Set initial video audio parameters
    video.volume = savedVol;
    // Always start muted initially so browser allows background autoplay without blocking
    video.muted = true;
    isMuted = true;

    // Build Floating Sound Controller Widget DOM
    const widget = document.createElement('div');
    widget.className = 'bgm-floating-widget';
    widget.id = 'bgmWidget';
    widget.setAttribute('role', 'region');
    widget.setAttribute('aria-label', 'Background Video Sound Controls');

    widget.innerHTML = `
      <div class="bgm-disc" id="bgmDiscBtn" title="Sound Control (Click to Mute/Unmute)">
        <img src="logo.png" alt="SS EMPIRE" class="bgm-logo-img">
      </div>

      <div class="bgm-controls-drawer" id="bgmDrawer">
        <!-- Sound wave visualizer -->
        <div class="bgm-waves" id="bgmWaves" title="Audio Status">
          <span></span><span></span><span></span><span></span>
        </div>

        <!-- Main Mute/Unmute Toggle (Replaces pause with sound mute) -->
        <button type="button" class="bgm-toggle-btn" id="bgmMuteToggleBtn" title="Mute / Unmute Sound">
          <!-- Unmuted / Sound On Icon -->
          <svg id="iconSoundOn" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
          </svg>
          <!-- Muted / Sound Off Icon -->
          <svg id="iconSoundMuted" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <line x1="23" y1="9" x2="17" y2="15"></line>
            <line x1="17" y1="9" x2="23" y2="15"></line>
          </svg>
        </button>

        <!-- Volume Slider Wrap -->
        <div class="bgm-vol-wrap">
          <input 
            type="range" 
            id="bgmSlider" 
            class="bgm-vol-slider" 
            min="0" 
            max="1" 
            step="0.02" 
            value="${savedVol}" 
            title="Drag to Adjust Volume"
          >
        </div>

        <!-- Volume Level Badge -->
        <span class="bgm-vol-text" id="bgmVolPct">${Math.round(savedVol * 100)}%</span>
      </div>
    `;

    document.body.appendChild(widget);

    // Elements
    const discBtn = document.getElementById('bgmDiscBtn');
    const muteToggleBtn = document.getElementById('bgmMuteToggleBtn');
    const slider = document.getElementById('bgmSlider');
    const volPctText = document.getElementById('bgmVolPct');
    const iconSoundOn = document.getElementById('iconSoundOn');
    const iconSoundMuted = document.getElementById('iconSoundMuted');

    function updateUi(active) {
      isMuted = !active;
      if (active) {
        widget.classList.add('playing');
        iconSoundOn.style.display = 'block';
        iconSoundMuted.style.display = 'none';
        discBtn.title = "Sound Active (Click to Mute)";
        muteToggleBtn.title = "Mute Sound";
      } else {
        widget.classList.remove('playing');
        iconSoundOn.style.display = 'none';
        iconSoundMuted.style.display = 'block';
        discBtn.title = "Sound Muted (Click to Unmute)";
        muteToggleBtn.title = "Unmute Sound";
      }
    }

    function updateSliderFill(val) {
      const pct = Math.round(val * 100);
      slider.style.setProperty('--vol-fill', pct + '%');
      if (volPctText) {
        volPctText.textContent = (isMuted ? 'MUTE' : (pct + '%'));
      }
    }
    updateSliderFill(savedVol);

    function setVolume(val, unmuteIfZero = false) {
      val = Math.max(0, Math.min(1, Math.round(val * 20) / 20));
      video.volume = val;
      savedVol = val;
      slider.value = val;
      localStorage.setItem('ssempire_video_vol', val);

      if (val === 0) {
        video.muted = true;
        updateUi(false);
      } else {
        if (unmuteIfZero || isMuted) {
          video.muted = false;
          updateUi(true);
          localStorage.setItem('ssempire_video_muted', 'false');
        }
      }
      updateSliderFill(val);
    }

    function toggleMute() {
      if (!video) return;

      if (!video.muted && video.volume > 0) {
        // Mute
        video.muted = true;
        updateUi(false);
        updateSliderFill(savedVol);
        localStorage.setItem('ssempire_video_muted', 'true');
      } else {
        // Unmute
        video.muted = false;
        if (video.volume === 0) {
          setVolume(savedVol > 0 ? savedVol : DEFAULT_VOL);
        }
        updateUi(true);
        updateSliderFill(video.volume);
        localStorage.setItem('ssempire_video_muted', 'false');

        // Ensure video is playing
        if (video.paused) {
          video.play().catch(() => {});
        }
      }
    }

    // Toggle button click
    muteToggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleMute();
    });

    // Disc click
    discBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.matchMedia('(hover: none)').matches) {
        // On touch screens, tap toggles drawer expansion
        widget.classList.toggle('expanded');
      } else {
        toggleMute();
      }
    });

    // Slider Dragging
    let isDragging = false;
    slider.addEventListener('mousedown', () => { isDragging = true; });
    slider.addEventListener('touchstart', () => { isDragging = true; }, { passive: true });
    window.addEventListener('mouseup', () => { isDragging = false; });
    window.addEventListener('touchend', () => { isDragging = false; });

    slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      setVolume(val, val > 0);
    });

    // Click outside to collapse on touch devices
    document.addEventListener('click', (e) => {
      if (!widget.contains(e.target)) {
        widget.classList.remove('expanded');
      }
    });

    // 4. Autounmute on first user gesture if user wants sound
    function onFirstGesture() {
      if (wantsSound && video.muted) {
        video.muted = false;
        video.volume = savedVol > 0 ? savedVol : DEFAULT_VOL;
        updateUi(true);
        updateSliderFill(video.volume);
      }
      cleanupGestureListeners();
    }

    function cleanupGestureListeners() {
      ['click', 'pointerdown', 'touchstart', 'keydown'].forEach(evt => {
        document.removeEventListener(evt, onFirstGesture, true);
        window.removeEventListener(evt, onFirstGesture, true);
      });
    }

    ['click', 'pointerdown', 'touchstart', 'keydown'].forEach(evt => {
      document.addEventListener(evt, onFirstGesture, { capture: true, once: true });
      window.addEventListener(evt, onFirstGesture, { capture: true, once: true });
    });

    // If already unmuted somehow
    if (!video.muted && !video.paused) {
      updateUi(true);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initController);
  } else {
    initController();
  }
})();
