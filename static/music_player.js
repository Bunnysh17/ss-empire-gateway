// SS EMPIRE - Floating Background Music Player
// Featuring Suyash Logo, Instant Autoplay, No Title Text, Play/Pause, Volume Slider

(function() {
  const AUDIO_SRC = 'bgm.mp3';
  const DEFAULT_VOL = 0.5;

  let audio = null;
  let isPlaying = false;
  let savedVol = parseFloat(localStorage.getItem('ssempire_bgm_vol'));
  if (isNaN(savedVol) || savedVol === null) {
    savedVol = DEFAULT_VOL;
  }

  function initPlayer() {
    if (document.getElementById('bgmWidget')) return;

    // 1. Create Audio Element
    audio = document.createElement('audio');
    audio.id = 'ssEmpireBgm';
    audio.src = AUDIO_SRC;
    audio.loop = true;
    audio.preload = 'auto';
    audio.volume = savedVol;
    document.body.appendChild(audio);

    // 2. Create Floating Widget DOM (Minimalist: Suyash Logo + Waves + Play/Pause + Volume)
    const widget = document.createElement('div');
    widget.className = 'bgm-floating-widget';
    widget.id = 'bgmWidget';
    widget.innerHTML = `
      <div class="bgm-disc" id="bgmDiscBtn" title="SS EMPIRE - Suyash (Click to Toggle Music)">
        <img src="logo.png" alt="Suyash" class="bgm-logo-img">
      </div>

      <div class="bgm-waves" id="bgmWaves" title="Music Status">
        <span></span><span></span><span></span><span></span>
      </div>

      <button class="bgm-toggle-btn" id="bgmPlayBtn" title="Play / Pause">
        <svg id="iconBgmPlay" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="display:none;">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <svg id="iconBgmPause" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="4" width="4" height="16"></rect>
          <rect x="14" y="4" width="4" height="16"></rect>
        </svg>
      </button>

      <div class="bgm-vol-wrap">
        <button class="bgm-mute-btn" id="bgmMuteBtn" title="Mute / Unmute">
          <svg id="iconVolHigh" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          <svg id="iconVolMuted" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <line x1="23" y1="9" x2="17" y2="15"></line>
            <line x1="17" y1="9" x2="23" y2="15"></line>
          </svg>
        </button>
        <input 
          type="range" 
          id="bgmSlider" 
          class="bgm-vol-slider" 
          min="0" 
          max="1" 
          step="0.01" 
          value="${savedVol}" 
          title="Volume Control"
        >
      </div>
    `;
    document.body.appendChild(widget);

    // 3. Bind UI Controls
    const playBtn = document.getElementById('bgmPlayBtn');
    const discBtn = document.getElementById('bgmDiscBtn');
    const slider = document.getElementById('bgmSlider');
    const muteBtn = document.getElementById('bgmMuteBtn');
    const iconPlay = document.getElementById('iconBgmPlay');
    const iconPause = document.getElementById('iconBgmPause');
    const iconHigh = document.getElementById('iconVolHigh');
    const iconMuted = document.getElementById('iconVolMuted');

    function updateUi(playing) {
      isPlaying = playing;
      if (playing) {
        widget.classList.add('playing');
        iconPlay.style.display = 'none';
        iconPause.style.display = 'block';
      } else {
        widget.classList.remove('playing');
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
      }
    }

    function togglePlay() {
      if (isPlaying) {
        audio.pause();
        updateUi(false);
      } else {
        audio.play().then(() => {
          updateUi(true);
        }).catch(() => {});
      }
    }

    playBtn.addEventListener('click', togglePlay);
    discBtn.addEventListener('click', togglePlay);

    // Volume Slider
    slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      audio.volume = val;
      savedVol = val;
      localStorage.setItem('ssempire_bgm_vol', val);

      if (val === 0) {
        iconHigh.style.display = 'none';
        iconMuted.style.display = 'block';
      } else {
        iconHigh.style.display = 'block';
        iconMuted.style.display = 'none';
        if (!isPlaying) {
          audio.play().then(() => updateUi(true)).catch(() => {});
        }
      }
    });

    // Mute Toggle
    muteBtn.addEventListener('click', () => {
      if (audio.volume > 0) {
        audio.volume = 0;
        slider.value = 0;
        iconHigh.style.display = 'none';
        iconMuted.style.display = 'block';
      } else {
        const restore = savedVol > 0 ? savedVol : DEFAULT_VOL;
        audio.volume = restore;
        slider.value = restore;
        iconHigh.style.display = 'block';
        iconMuted.style.display = 'none';
      }
    });

    // 4. Instant Autoplay on website load + first click/touch trigger
    function forceAutoplay() {
      function tryPlay() {
        const p = audio.play();
        if (p !== undefined) {
          p.then(() => {
            updateUi(true);
            cleanupListeners();
          }).catch(() => {
            updateUi(false);
          });
        }
      }

      function onFirstUserGesture() {
        tryPlay();
      }

      function cleanupListeners() {
        const events = ['click', 'pointerdown', 'mousedown', 'touchstart', 'touchend', 'keydown'];
        events.forEach(evt => {
          document.removeEventListener(evt, onFirstUserGesture, true);
          window.removeEventListener(evt, onFirstUserGesture, true);
        });
      }

      // 1. Try playing immediately on page load
      tryPlay();

      // 2. Intercept ANY click or touch anywhere on the page immediately
      const events = ['click', 'pointerdown', 'mousedown', 'touchstart', 'touchend', 'keydown'];
      events.forEach(evt => {
        document.addEventListener(evt, onFirstUserGesture, { capture: true });
        window.addEventListener(evt, onFirstUserGesture, { capture: true });
      });
    }

    forceAutoplay();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPlayer);
  } else {
    initPlayer();
  }
})();
