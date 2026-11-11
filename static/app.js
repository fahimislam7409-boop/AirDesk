// AetherDesk Client - Perfect Viewport & Chrome Remote Desktop Architecture

(() => {
  // Elements
  const displayContainer = document.getElementById("display-container");
  const remoteVideo = document.getElementById("remote-video");
  const remoteCanvas = document.getElementById("remote-canvas");
  const canvasCtx = remoteCanvas.getContext("2d");
  const touchIndicator = document.getElementById("touch-indicator");

  // Splash & Login
  const splashOverlay = document.getElementById("splash-overlay");
  const splashStatus = document.getElementById("splash-status");
  const loginSection = document.getElementById("login-section");
  const pinInput = document.getElementById("pin-input");
  const btnLogin = document.getElementById("btn-login");
  const loginError = document.getElementById("login-error");

  // FAB Menu & Status
  const fabMenu = document.getElementById("fab-menu");
  const fabStatusDot = document.getElementById("fab-status-dot");

  // Slide-out Control Center Panel
  const controlPanel = document.getElementById("control-panel");
  const btnClosePanel = document.getElementById("btn-close-panel");
  const panelPcInfo = document.getElementById("panel-pc-info");

  // Viewport Scaling Buttons
  const scaleFitBtn = document.getElementById("scale-fit-btn");
  const scaleFillBtn = document.getElementById("scale-fill-btn");

  // Panel Buttons
  const modeTrackpadBtn = document.getElementById("mode-trackpad-btn");
  const modeTouchBtn = document.getElementById("mode-touch-btn");
  const btnOpenKbd = document.getElementById("btn-open-kbd");
  const btnOpenActions = document.getElementById("btn-open-actions");
  const btnToggleSideMouse = document.getElementById("btn-toggle-side-mouse");
  const sideMouseLabel = document.getElementById("side-mouse-label");
  const btnFullscreenPanel = document.getElementById("btn-fullscreen-panel");
  const btnDisconnect = document.getElementById("btn-disconnect");

  // Performance Settings
  const settingFps = document.getElementById("setting-fps");
  const settingQuality = document.getElementById("setting-quality");
  const settingSens = document.getElementById("setting-sens");
  const sensLabel = document.getElementById("sens-label");

  // Side Mouse Bar
  const sideMouseBar = document.getElementById("side-mouse-bar");
  const sideBtnLeft = document.getElementById("side-btn-left");
  const sideBtnRight = document.getElementById("side-btn-right");
  const sideScrollWidget = document.getElementById("side-scroll-widget");
  const sideScrollThumb = document.getElementById("side-scroll-thumb");
  const sideBtnHide = document.getElementById("side-btn-hide");

  // Keyboard Drawer
  const keyboardDrawer = document.getElementById("keyboard-drawer");
  const btnCloseKbd = document.getElementById("btn-close-kbd");
  const typeTextInput = document.getElementById("type-text-input");
  const btnSendText = document.getElementById("btn-send-text");

  // Actions Modal
  const actionsModal = document.getElementById("actions-modal");
  const btnCloseActions = document.getElementById("btn-close-actions");

  // State
  let token = localStorage.getItem("aether_token") || "";
  let pcWidth = 1920;
  let pcHeight = 1080;
  let controlMode = localStorage.getItem("aether_mode") || "touchpad";
  let scaleMode = localStorage.getItem("aether_scale_mode") || "fit"; // "fit" (guarantees taskbar) vs "fill"
  let sensitivity = parseFloat(localStorage.getItem("aether_sens") || "1.2");
  let showSideMouse = localStorage.getItem("aether_side_mouse") === "true";

  let viewportX = 0, viewportY = 0, viewportW = 0, viewportH = 0;

  let ws = null;
  let pingInterval = null;
  let lastPingTime = 0;
  let currentRtt = 0;
  let frameCount = 0;
  let currentFps = 0;
  let fpsTimer = null;
  let firstFrameRendered = false;
  let activeModifiers = new Set();
  let fabIdleTimer = null;

  function init() {
    updateModeUI();
    updateScaleUI();
    settingSens.value = sensitivity;
    sensLabel.textContent = sensitivity.toFixed(1) + "x";

    if (showSideMouse) {
      sideMouseBar.classList.add("visible");
      sideMouseLabel.textContent = "Hide Side Bar";
      btnToggleSideMouse.classList.add("active");
    }

    updateViewportLayout();
    window.addEventListener("resize", updateViewportLayout);
    window.addEventListener("orientationchange", () => setTimeout(updateViewportLayout, 100));

    setupEvents();
    setupFabDragging();

    if (!token) {
      showLoginPrompt();
    } else {
      checkAuthAndConnect();
    }
  }

  // --- Viewport Layout (Guarantees Taskbar Is 100% Inside Screen) ---

  function updateViewportLayout() {
    const winW = window.innerWidth;
    const winH = window.innerHeight;

    if (scaleMode === "fill") {
      viewportX = 0;
      viewportY = 0;
      viewportW = winW;
      viewportH = winH;
    } else {
      // "fit" mode: Mathematically guarantees the entire 1080p desktop (including taskbar) is visible!
      const pcAspect = pcWidth / pcHeight; // 1920 / 1080 = 1.777778
      const screenAspect = winW / winH;

      if (screenAspect > pcAspect) {
        // Screen is wider than PC: letterbox on sides
        viewportH = winH;
        viewportW = Math.round(winH * pcAspect);
        viewportX = Math.round((winW - viewportW) / 2);
        viewportY = 0;
      } else {
        // Screen is taller than PC (16:10 or 4:3 tablet): letterbox on top & bottom
        viewportW = winW;
        viewportH = Math.round(winW / pcAspect);
        viewportX = 0;
        viewportY = Math.round((winH - viewportH) / 2);
      }
    }

    remoteCanvas.style.width = `${viewportW}px`;
    remoteCanvas.style.height = `${viewportH}px`;
    remoteCanvas.style.left = `${viewportX}px`;
    remoteCanvas.style.top = `${viewportY}px`;

    remoteVideo.style.width = `${viewportW}px`;
    remoteVideo.style.height = `${viewportH}px`;
    remoteVideo.style.left = `${viewportX}px`;
    remoteVideo.style.top = `${viewportY}px`;
  }

  function updateScaleUI() {
    if (scaleMode === "fit") {
      scaleFitBtn.classList.add("active");
      scaleFillBtn.classList.remove("active");
    } else {
      scaleFitBtn.classList.remove("active");
      scaleFillBtn.classList.add("active");
    }
  }

  function updateModeUI() {
    if (controlMode === "touchpad") {
      modeTrackpadBtn.classList.add("active");
      modeTouchBtn.classList.remove("active");
    } else {
      modeTrackpadBtn.classList.remove("active");
      modeTouchBtn.classList.add("active");
    }
  }

  function getScreenCoordinates(clientX, clientY) {
    if (viewportW <= 0 || viewportH <= 0) return { x: 0, y: 0 };
    const normX = Math.max(0, Math.min(1, (clientX - viewportX) / viewportW));
    const normY = Math.max(0, Math.min(1, (clientY - viewportY) / viewportH));
    return {
      x: Math.round(normX * pcWidth),
      y: Math.round(normY * pcHeight)
    };
  }

  function showTouchRipple(x, y) {
    touchIndicator.style.left = `${x}px`;
    touchIndicator.style.top = `${y}px`;
    touchIndicator.classList.add("active");
    setTimeout(() => touchIndicator.classList.remove("active"), 200);
  }

  // --- Login & Auth ---

  function showLoginPrompt(errorMsg = "") {
    splashOverlay.classList.add("open");
    splashStatus.textContent = "Security Verification";
    loginSection.style.display = "flex";
    if (errorMsg) loginError.textContent = errorMsg;
    pinInput.value = "";
    pinInput.focus();
  }

  function hideSplash() {
    splashOverlay.classList.remove("open");
    loginSection.style.display = "none";
    loginError.textContent = "";
  }

  async function checkAuthAndConnect() {
    splashOverlay.classList.add("open");
    splashStatus.textContent = "Connecting to desktop...";
    loginSection.style.display = "none";

    try {
      const res = await fetch(`/api/info?token=${token}`);
      if (res.status === 401) {
        showLoginPrompt("Session expired. Please enter PIN.");
        return;
      }
      const data = await res.json();
      pcWidth = data.screen_width || 1920;
      pcHeight = data.screen_height || 1080;
      updateViewportLayout();
      connect();
    } catch (e) {
      console.warn("Could not reach /api/info, connecting directly:", e);
      connect();
    }
  }

  async function doLogin() {
    const pin = pinInput.value.trim();
    if (!pin) {
      loginError.textContent = "Please enter PIN";
      return;
    }
    try {
      loginError.textContent = "";
      splashStatus.textContent = "Verifying PIN...";
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin })
      });
      const data = await res.json();
      if (data.success && data.token) {
        token = data.token;
        localStorage.setItem("aether_token", token);
        splashStatus.textContent = "Connecting to desktop...";
        loginSection.style.display = "none";
        connect();
      } else {
        showLoginPrompt(data.message || "Invalid PIN");
      }
    } catch (e) {
      showLoginPrompt("Cannot connect to server. Check IP & port.");
    }
  }

  // --- Network Connection (Ultra Low Latency Turbo Stream) ---

  function connect() {
    disconnect();
    firstFrameRendered = false;
    fabStatusDot.className = "fab-badge";

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(wsUrl);
    ws.binaryType = "blob";

    ws.onopen = () => {
      fabStatusDot.className = "fab-badge connected";
      startPing();
    };

    ws.onmessage = async (evt) => {
      if (typeof evt.data === "string") {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "pong") {
            currentRtt = Math.round(performance.now() - msg.t);
            updatePanelStatus();
          } else if (msg.type === "init") {
            pcWidth = msg.width;
            pcHeight = msg.height;
            updateViewportLayout();
          }
        } catch (e) {}
      } else if (evt.data instanceof Blob) {
        try {
          const imgBitmap = await createImageBitmap(evt.data);
          if (remoteCanvas.width !== imgBitmap.width || remoteCanvas.height !== imgBitmap.height) {
            remoteCanvas.width = imgBitmap.width;
            remoteCanvas.height = imgBitmap.height;
            pcWidth = imgBitmap.width;
            pcHeight = imgBitmap.height;
            updateViewportLayout();
          }
          canvasCtx.drawImage(imgBitmap, 0, 0);
          frameCount++;

          if (!firstFrameRendered) {
            firstFrameRendered = true;
            hideSplash();
          }
        } catch (err) {
          const url = URL.createObjectURL(evt.data);
          const img = new Image();
          img.onload = () => {
            if (remoteCanvas.width !== img.width || remoteCanvas.height !== img.height) {
              remoteCanvas.width = img.width;
              remoteCanvas.height = img.height;
              pcWidth = img.width;
              pcHeight = img.height;
              updateViewportLayout();
            }
            canvasCtx.drawImage(img, 0, 0);
            URL.revokeObjectURL(url);
            frameCount++;
            if (!firstFrameRendered) {
              firstFrameRendered = true;
              hideSplash();
            }
          };
          img.src = url;
        }
      }
    };

    ws.onclose = () => {
      fabStatusDot.className = "fab-badge error";
      updatePanelStatus();
    };

    ws.onerror = () => {
      fabStatusDot.className = "fab-badge error";
    };

    startFpsCounter();
  }

  function disconnect() {
    if (ws) {
      try { ws.close(); } catch (e) {}
      ws = null;
    }
    if (pingInterval) clearInterval(pingInterval);
    if (fpsTimer) clearInterval(fpsTimer);
  }

  function sendWs(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  function startPing() {
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        lastPingTime = performance.now();
        sendWs({ type: "ping", t: lastPingTime });
      }
    }, 2000);
  }

  function startFpsCounter() {
    if (fpsTimer) clearInterval(fpsTimer);
    frameCount = 0;
    fpsTimer = setInterval(() => {
      currentFps = frameCount;
      frameCount = 0;
      updatePanelStatus();
    }, 1000);
  }

  function updatePanelStatus() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      panelPcInfo.textContent = `Connected (${currentRtt} ms) • ${currentFps} FPS`;
    } else {
      panelPcInfo.textContent = "Disconnected";
    }
  }

  // --- Natural Touch & Gesture Engine (Chrome Remote Desktop Style) ---

  function setupTouchEvents() {
    let startX = 0, startY = 0;
    let lastX = 0, lastY = 0;
    let touchStartTime = 0;
    let isMoving = false;
    let isDragging = false;
    let longPressTimer = null;
    let lastTapTime = 0;
    let twoFingerStartY = 0;

    const resetFabIdle = () => {
      fabMenu.classList.remove("idle-dim");
      if (fabIdleTimer) clearTimeout(fabIdleTimer);
      fabIdleTimer = setTimeout(() => {
        fabMenu.classList.add("idle-dim");
      }, 3500);
    };

    resetFabIdle();

    displayContainer.addEventListener("touchstart", (e) => {
      e.preventDefault();
      resetFabIdle();
      const touches = e.touches;

      if (touches.length === 1) {
        const t = touches[0];
        startX = t.clientX;
        startY = t.clientY;
        lastX = t.clientX;
        lastY = t.clientY;
        touchStartTime = performance.now();
        isMoving = false;

        if (controlMode === "touch") {
          // Direct Touch: tap directly on icon/window/taskbar
          const coords = getScreenCoordinates(t.clientX, t.clientY);
          sendWs({ type: "move", x: coords.x, y: coords.y });
          sendWs({ type: "mousedown", button: "left" });
          isDragging = true;
          showTouchRipple(t.clientX, t.clientY);

          longPressTimer = setTimeout(() => {
            if (!isMoving) {
              sendWs({ type: "mouseup", button: "left" });
              sendWs({ type: "click", button: "right" });
              isDragging = false;
              showTouchRipple(t.clientX, t.clientY);
            }
          }, 500);
        } else {
          // Trackpad: long press triggers click-and-drag
          longPressTimer = setTimeout(() => {
            if (!isMoving) {
              sendWs({ type: "mousedown", button: "left" });
              isDragging = true;
              showTouchRipple(t.clientX, t.clientY);
            }
          }, 400);
        }
      } else if (touches.length === 2) {
        if (longPressTimer) clearTimeout(longPressTimer);
        if (isDragging) {
          sendWs({ type: "mouseup", button: "left" });
          isDragging = false;
        }
        twoFingerStartY = (touches[0].clientY + touches[1].clientY) / 2;
      }
    }, { passive: false });

    displayContainer.addEventListener("touchmove", (e) => {
      e.preventDefault();
      resetFabIdle();
      const touches = e.touches;

      if (touches.length === 1) {
        const t = touches[0];
        const dx = t.clientX - lastX;
        const dy = t.clientY - lastY;
        const totalDist = Math.hypot(t.clientX - startX, t.clientY - startY);

        if (totalDist > 8) {
          isMoving = true;
          if (longPressTimer) clearTimeout(longPressTimer);
        }

        if (controlMode === "touchpad") {
          sendWs({ type: "delta", dx: dx, dy: dy, sens: sensitivity });
        } else {
          const coords = getScreenCoordinates(t.clientX, t.clientY);
          sendWs({ type: "move", x: coords.x, y: coords.y });
        }

        lastX = t.clientX;
        lastY = t.clientY;
      } else if (touches.length === 2) {
        // Two finger scroll
        const currentMidY = (touches[0].clientY + touches[1].clientY) / 2;
        const dy = currentMidY - twoFingerStartY;
        if (Math.abs(dy) > 3) {
          sendWs({ type: "wheel", dy: Math.round(dy * 4), dx: 0 });
          twoFingerStartY = currentMidY;
        }
      }
    }, { passive: false });

    displayContainer.addEventListener("touchend", (e) => {
      e.preventDefault();
      resetFabIdle();
      if (longPressTimer) clearTimeout(longPressTimer);

      const elapsed = performance.now() - touchStartTime;

      if (e.touches.length === 0) {
        if (controlMode === "touchpad") {
          if (isDragging) {
            sendWs({ type: "mouseup", button: "left" });
            isDragging = false;
          } else if (!isMoving && elapsed < 300) {
            const now = performance.now();
            if (now - lastTapTime < 320) {
              sendWs({ type: "double_click", button: "left" });
              lastTapTime = 0;
            } else {
              sendWs({ type: "click", button: "left" });
              lastTapTime = now;
            }
            showTouchRipple(startX, startY);
          }
        } else {
          if (isDragging) {
            sendWs({ type: "mouseup", button: "left" });
            isDragging = false;
          }
        }
      } else if (e.touches.length === 1 && !isMoving && elapsed < 350) {
        sendWs({ type: "click", button: "right" });
        showTouchRipple(startX, startY);
      }
    }, { passive: false });
  }

  // --- Side Mouse Bar (Vertical in Margin) ---

  function setupSideMouseBar() {
    sideBtnLeft.addEventListener("click", () => sendWs({ type: "click", button: "left" }));
    sideBtnRight.addEventListener("click", () => sendWs({ type: "click", button: "right" }));

    sideBtnHide.addEventListener("click", () => {
      sideMouseBar.classList.remove("visible");
      showSideMouse = false;
      localStorage.setItem("aether_side_mouse", "false");
      sideMouseLabel.textContent = "Side Mouse";
      btnToggleSideMouse.classList.remove("active");
    });

    let isScrolling = false;
    let sliderStartY = 0;

    const onStart = (e) => {
      isScrolling = true;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      sliderStartY = clientY;
      e.stopPropagation();
    };

    const onMove = (e) => {
      if (!isScrolling) return;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const dy = clientY - sliderStartY;
      if (Math.abs(dy) > 2) {
        sendWs({ type: "wheel", dy: -Math.round(dy * 5), dx: 0 });
        sliderStartY = clientY;
        sideScrollThumb.style.transform = `translateY(${Math.max(-18, Math.min(18, dy))}px)`;
      }
      e.stopPropagation();
    };

    const onEnd = () => {
      isScrolling = false;
      sideScrollThumb.style.transform = "translateY(-50%)";
    };

    sideScrollWidget.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: true });
    window.addEventListener("touchend", onEnd);

    sideScrollWidget.addEventListener("mousedown", onStart);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onEnd);
  }

  // --- FAB Menu Dragging & Positioning ---

  function setupFabDragging() {
    const savedX = localStorage.getItem("aether_fab_x");
    const savedY = localStorage.getItem("aether_fab_y");
    if (savedX && savedY) {
      fabMenu.style.left = `${savedX}px`;
      fabMenu.style.top = `${savedY}px`;
      fabMenu.style.right = "auto";
    }

    let isDraggingFab = false;
    let fabMoved = false;
    let startFabX = 0, startFabY = 0;
    let offsetX = 0, offsetY = 0;

    const onStart = (e) => {
      isDraggingFab = true;
      fabMoved = false;
      fabMenu.classList.remove("idle-dim");
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const rect = fabMenu.getBoundingClientRect();
      startFabX = clientX;
      startFabY = clientY;
      offsetX = clientX - rect.left;
      offsetY = clientY - rect.top;
      e.stopPropagation();
    };

    const onMove = (e) => {
      if (!isDraggingFab) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      if (Math.hypot(clientX - startFabX, clientY - startFabY) > 8) {
        fabMoved = true;
      }

      let newX = clientX - offsetX;
      let newY = clientY - offsetY;

      const maxW = window.innerWidth - fabMenu.offsetWidth - 8;
      const maxH = window.innerHeight - fabMenu.offsetHeight - 8;
      newX = Math.max(8, Math.min(maxW, newX));
      newY = Math.max(8, Math.min(maxH, newY));

      fabMenu.style.left = `${newX}px`;
      fabMenu.style.top = `${newY}px`;
      fabMenu.style.right = "auto";
      e.stopPropagation();
    };

    const onEnd = (e) => {
      if (!isDraggingFab) return;
      isDraggingFab = false;
      if (fabMoved) {
        const rect = fabMenu.getBoundingClientRect();
        localStorage.setItem("aether_fab_x", Math.round(rect.left));
        localStorage.setItem("aether_fab_y", Math.round(rect.top));
      } else {
        controlPanel.classList.toggle("open");
      }
    };

    fabMenu.addEventListener("touchstart", onStart, { passive: false });
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onEnd);

    fabMenu.addEventListener("mousedown", onStart);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onEnd);
  }

  // --- Events & Panel Actions ---

  function setupEvents() {
    setupTouchEvents();
    setupSideMouseBar();

    // Login
    btnLogin.addEventListener("click", doLogin);
    pinInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doLogin();
    });

    // Control Panel
    btnClosePanel.addEventListener("click", () => controlPanel.classList.remove("open"));

    // Screen Scale Mode (Fit vs Fill)
    scaleFitBtn.addEventListener("click", () => {
      scaleMode = "fit";
      localStorage.setItem("aether_scale_mode", "fit");
      updateScaleUI();
      updateViewportLayout();
    });

    scaleFillBtn.addEventListener("click", () => {
      scaleMode = "fill";
      localStorage.setItem("aether_scale_mode", "fill");
      updateScaleUI();
      updateViewportLayout();
    });

    modeTrackpadBtn.addEventListener("click", () => {
      controlMode = "touchpad";
      localStorage.setItem("aether_mode", "touchpad");
      updateModeUI();
    });

    modeTouchBtn.addEventListener("click", () => {
      controlMode = "touch";
      localStorage.setItem("aether_mode", "touch");
      updateModeUI();
    });

    btnOpenKbd.addEventListener("click", () => {
      controlPanel.classList.remove("open");
      keyboardDrawer.classList.add("open");
      typeTextInput.focus();
    });

    btnOpenActions.addEventListener("click", () => {
      controlPanel.classList.remove("open");
      actionsModal.classList.add("open");
    });

    btnToggleSideMouse.addEventListener("click", () => {
      showSideMouse = !showSideMouse;
      localStorage.setItem("aether_side_mouse", showSideMouse);
      if (showSideMouse) {
        sideMouseBar.classList.add("visible");
        sideMouseLabel.textContent = "Hide Side Bar";
        btnToggleSideMouse.classList.add("active");
      } else {
        sideMouseBar.classList.remove("visible");
        sideMouseLabel.textContent = "Side Mouse";
        btnToggleSideMouse.classList.remove("active");
      }
    });

    btnFullscreenPanel.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
          setTimeout(updateViewportLayout, 200);
        }).catch(() => {});
      } else {
        document.exitFullscreen().then(() => {
          setTimeout(updateViewportLayout, 200);
        }).catch(() => {});
      }
    });

    settingFps.addEventListener("change", () => {
      sendWs({ type: "settings", fps: parseInt(settingFps.value) });
    });

    settingQuality.addEventListener("change", () => {
      sendWs({ type: "settings", quality: parseInt(settingQuality.value) });
    });

    settingSens.addEventListener("input", () => {
      sensitivity = parseFloat(settingSens.value);
      sensLabel.textContent = sensitivity.toFixed(1) + "x";
      localStorage.setItem("aether_sens", sensitivity);
    });

    btnDisconnect.addEventListener("click", () => {
      localStorage.removeItem("aether_token");
      token = "";
      disconnect();
      controlPanel.classList.remove("open");
      showLoginPrompt("Disconnected.");
    });

    // Keyboard Drawer
    btnCloseKbd.addEventListener("click", () => keyboardDrawer.classList.remove("open"));

    btnSendText.addEventListener("click", () => {
      const text = typeTextInput.value;
      if (text) {
        sendWs({ type: "type", text: text });
        typeTextInput.value = "";
      }
    });

    typeTextInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") btnSendText.click();
    });

    document.querySelectorAll(".kbd-key").forEach((keyEl) => {
      const keyName = keyEl.getAttribute("data-key");
      if (keyEl.classList.contains("toggle-key")) {
        keyEl.addEventListener("click", () => {
          if (activeModifiers.has(keyName)) {
            activeModifiers.delete(keyName);
            keyEl.classList.remove("active");
            sendWs({ type: "keyup", key: keyName });
          } else {
            activeModifiers.add(keyName);
            keyEl.classList.add("active");
            sendWs({ type: "keydown", key: keyName });
          }
        });
      } else {
        keyEl.addEventListener("click", () => {
          sendWs({ type: "press", key: keyName });
        });
      }
    });

    // Actions Modal
    btnCloseActions.addEventListener("click", () => actionsModal.classList.remove("open"));
    actionsModal.addEventListener("click", (e) => {
      if (e.target === actionsModal) actionsModal.classList.remove("open");
    });

    document.querySelectorAll(".action-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const act = btn.getAttribute("data-action");
        sendWs({ type: "action", action: act });
        setTimeout(() => actionsModal.classList.remove("open"), 150);
      });
    });
  }

  window.addEventListener("DOMContentLoaded", init);
})();
