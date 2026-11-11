package com.aetherdesk.remote;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class MainActivity extends Activity {

    private static final String PREFS_NAME = "AetherDeskPrefs";
    private static final String KEY_HOST = "host_ip";
    private static final String KEY_PORT = "port";
    private static final String KEY_PIN = "pin";

    private LinearLayout dashboardLayout;
    private EditText inputHost;
    private EditText inputPort;
    private EditText inputPin;
    private Button btnConnect;
    private Button btnDiscover;
    private TextView txtStatus;
    private WebView remoteWebView;
    private Button btnExitSession;

    private SharedPreferences prefs;
    private ExecutorService networkExecutor;
    private Handler mainHandler;
    private boolean isScanning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Keep screen on while using remote desktop
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        networkExecutor = Executors.newFixedThreadPool(8);
        mainHandler = new Handler(Looper.getMainLooper());

        initViews();
        loadSavedConfig();
        setupWebView();
        setupListeners();
        hideSystemUI();
    }

    private void initViews() {
        dashboardLayout = findViewById(R.id.dashboard_layout);
        inputHost = findViewById(R.id.input_host);
        inputPort = findViewById(R.id.input_port);
        inputPin = findViewById(R.id.input_pin);
        btnConnect = findViewById(R.id.btn_connect);
        btnDiscover = findViewById(R.id.btn_discover);
        txtStatus = findViewById(R.id.txt_status);
        remoteWebView = findViewById(R.id.remote_webview);
        btnExitSession = findViewById(R.id.btn_exit_session);
    }

    private void loadSavedConfig() {
        String savedHost = prefs.getString(KEY_HOST, "");
        String savedPort = prefs.getString(KEY_PORT, "8000");
        String savedPin = prefs.getString(KEY_PIN, "123456");

        inputHost.setText(savedHost);
        inputPort.setText(savedPort);
        inputPin.setText(savedPin);

        if (savedHost.isEmpty()) {
            // First run on new device: auto-discover PC automatically!
            mainHandler.postDelayed(this::autoDiscoverPC, 400);
        } else {
            txtStatus.setText("● Ready to Connect (Auto-Saved: " + savedHost + ")");
            txtStatus.setTextColor(getResources().getColor(R.color.accent_cyan, getTheme()));
        }
    }

    private void saveConfig(String host, String port, String pin) {
        prefs.edit()
                .putString(KEY_HOST, host)
                .putString(KEY_PORT, port)
                .putString(KEY_PIN, pin)
                .apply();
    }

    private void setupWebView() {
        WebSettings ws = remoteWebView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setAllowFileAccess(true);
        ws.setAllowContentAccess(true);
        ws.setUseWideViewPort(true);
        ws.setLoadWithOverviewMode(true);
        ws.setSupportZoom(true);
        ws.setBuiltInZoomControls(false);
        ws.setDisplayZoomControls(false);

        // Enable hardware acceleration
        remoteWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        remoteWebView.setBackgroundColor(Color.BLACK);

        remoteWebView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                hideSystemUI();
                // Auto-fill PIN in the web app if needed
                final String pin = inputPin.getText().toString().trim();
                if (!pin.isEmpty()) {
                    String js = "setTimeout(function() {" +
                            "  var pinInput = document.getElementById('pin-input');" +
                            "  var loginBtn = document.getElementById('btn-login');" +
                            "  if (pinInput && loginBtn) {" +
                            "    pinInput.value = '" + pin + "';" +
                            "    loginBtn.click();" +
                            "  }" +
                            "}, 400);";
                    view.evaluateJavascript(js, null);
                }
            }
        });

        remoteWebView.setWebChromeClient(new WebChromeClient());
    }

    private void setupListeners() {
        btnConnect.setOnClickListener(v -> startSession());

        btnDiscover.setOnClickListener(v -> autoDiscoverPC());

        btnExitSession.setOnClickListener(v -> exitSession());
    }

    private void startSession() {
        String host = inputHost.getText().toString().trim();
        String port = inputPort.getText().toString().trim();
        String pin = inputPin.getText().toString().trim();

        if (host.isEmpty()) {
            Toast.makeText(this, "Please enter PC IP address or tap Auto Discover", Toast.LENGTH_SHORT).show();
            return;
        }

        saveConfig(host, port, pin);

        txtStatus.setText("● Connecting to " + host + ":" + port + "...");
        txtStatus.setTextColor(getResources().getColor(R.color.accent_amber, getTheme()));

        String targetUrl = "http://" + host + ":" + port + "/";

        dashboardLayout.setVisibility(View.GONE);
        remoteWebView.setVisibility(View.VISIBLE);
        btnExitSession.setVisibility(View.VISIBLE);

        hideSystemUI();
        remoteWebView.loadUrl(targetUrl);
    }

    private void exitSession() {
        remoteWebView.loadUrl("about:blank");
        remoteWebView.setVisibility(View.GONE);
        btnExitSession.setVisibility(View.GONE);
        dashboardLayout.setVisibility(View.VISIBLE);

        txtStatus.setText("● Ready to Connect");
        txtStatus.setTextColor(getResources().getColor(R.color.accent_cyan, getTheme()));
        hideSystemUI();
    }

    private void autoDiscoverPC() {
        if (isScanning) return;
        isScanning = true;

        btnDiscover.setEnabled(false);
        txtStatus.setText("🔍 Auto-detecting PC on local network...");
        txtStatus.setTextColor(getResources().getColor(R.color.accent_amber, getTheme()));

        final int port;
        try {
            port = Integer.parseInt(inputPort.getText().toString().trim());
        } catch (Exception e) {
            isScanning = false;
            btnDiscover.setEnabled(true);
            return;
        }

        networkExecutor.execute(() -> {
            String foundIp = null;
            String foundHostName = null;

            // 1. Ultra-fast UDP Beacon broadcast probe on UDP:8001
            WifiManager wifi = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            WifiManager.MulticastLock multicastLock = null;
            try {
                if (wifi != null) {
                    multicastLock = wifi.createMulticastLock("AetherDeskDiscovery");
                    multicastLock.setReferenceCounted(true);
                    multicastLock.acquire();
                }

                DatagramSocket socket = new DatagramSocket();
                socket.setBroadcast(true);
                socket.setSoTimeout(1200);

                byte[] sendData = "AETHERDESK_DISCOVER".getBytes(StandardCharsets.UTF_8);

                // Broadcast to global subnet broadcast
                DatagramPacket p1 = new DatagramPacket(sendData, sendData.length, InetAddress.getByName("255.255.255.255"), 8001);
                socket.send(p1);

                // Broadcast to local interface broadcast addresses
                for (InetAddress bcast : getBroadcastAddresses()) {
                    try {
                        socket.send(new DatagramPacket(sendData, sendData.length, bcast, 8001));
                    } catch (Exception ignored) {}
                }

                byte[] recvBuf = new byte[1024];
                DatagramPacket recvPacket = new DatagramPacket(recvBuf, recvBuf.length);
                socket.receive(recvPacket);

                String msg = new String(recvPacket.getData(), 0, recvPacket.getLength(), StandardCharsets.UTF_8);
                JSONObject json = new JSONObject(msg);
                if (json.has("ip")) {
                    foundIp = json.getString("ip");
                    foundHostName = json.optString("hostname", "PC");
                }
                socket.close();
            } catch (Exception ignored) {
                // UDP discovery timed out, fall through to subnet scan
            } finally {
                if (multicastLock != null && multicastLock.isHeld()) {
                    try { multicastLock.release(); } catch (Exception ignored) {}
                }
            }

            // 2. Fallback: Dynamic Subnet TCP Scan on Port 8000
            if (foundIp == null) {
                foundIp = scanSubnetForPort(port);
            }

            final String finalIp = foundIp;
            final String finalHostName = foundHostName;

            mainHandler.post(() -> {
                isScanning = false;
                btnDiscover.setEnabled(true);
                if (finalIp != null) {
                    inputHost.setText(finalIp);
                    String label = finalHostName != null ? finalHostName + " (" + finalIp + ")" : finalIp;
                    txtStatus.setText("✓ Detected PC: " + label);
                    txtStatus.setTextColor(getResources().getColor(R.color.accent_emerald, getTheme()));
                    Toast.makeText(MainActivity.this, "PC Detected: " + finalIp, Toast.LENGTH_SHORT).show();
                    saveConfig(finalIp, String.valueOf(port), inputPin.getText().toString().trim());
                } else {
                    txtStatus.setText("✕ Could not auto-detect PC. Ensure start.bat is running on PC.");
                    txtStatus.setTextColor(getResources().getColor(android.R.color.holo_red_light, getTheme()));
                    Toast.makeText(MainActivity.this, "Make sure PC and Tablet are on the same Wi-Fi.", Toast.LENGTH_LONG).show();
                }
            });
        });
    }

    private String scanSubnetForPort(int port) {
        String currentHost = inputHost.getText().toString().trim();
        List<String> prefixes = new ArrayList<>();

        if (!currentHost.isEmpty() && currentHost.contains(".")) {
            prefixes.add(currentHost.substring(0, currentHost.lastIndexOf('.') + 1));
        }

        // Dynamically get device's own local subnet prefixes
        for (String ip : getLocalIpAddresses()) {
            if (ip.contains(".")) {
                String pfx = ip.substring(0, ip.lastIndexOf('.') + 1);
                if (!prefixes.contains(pfx)) {
                    prefixes.add(pfx);
                }
            }
        }

        // Common router fallbacks
        if (!prefixes.contains("192.168.1.")) prefixes.add("192.168.1.");
        if (!prefixes.contains("192.168.0.")) prefixes.add("192.168.0.");

        AtomicReference<String> found = new AtomicReference<>(null);

        for (String prefix : prefixes) {
            // Quick check common desktop IPs
            String[] quickSuffixes = {"164", "100", "101", "102", "105", "2", "3", "4", "5", "10"};
            for (String s : quickSuffixes) {
                String testIp = prefix + s;
                if (isPortOpen(testIp, port, 120)) {
                    return testIp;
                }
            }

            // Parallel scan remainder of the subnet
            ExecutorService scanPool = Executors.newFixedThreadPool(24);
            CountDownLatch latch = new CountDownLatch(254);

            for (int i = 1; i <= 254; i++) {
                final String testIp = prefix + i;
                scanPool.execute(() -> {
                    try {
                        if (found.get() == null && isPortOpen(testIp, port, 90)) {
                            found.compareAndSet(null, testIp);
                        }
                    } finally {
                        latch.countDown();
                    }
                });
            }

            try {
                latch.await(2500, TimeUnit.MILLISECONDS);
            } catch (InterruptedException ignored) {}

            scanPool.shutdownNow();

            if (found.get() != null) {
                return found.get();
            }
        }

        return null;
    }

    private List<InetAddress> getBroadcastAddresses() {
        List<InetAddress> list = new ArrayList<>();
        try {
            for (Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces(); en.hasMoreElements(); ) {
                NetworkInterface intf = en.nextElement();
                if (intf.isLoopback() || !intf.isUp()) continue;
                for (InterfaceAddress addr : intf.getInterfaceAddresses()) {
                    if (addr.getBroadcast() != null) {
                        list.add(addr.getBroadcast());
                    }
                }
            }
        } catch (Exception ignored) {}
        return list;
    }

    private List<String> getLocalIpAddresses() {
        List<String> list = new ArrayList<>();
        try {
            for (Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces(); en.hasMoreElements(); ) {
                NetworkInterface intf = en.nextElement();
                if (intf.isLoopback() || !intf.isUp()) continue;
                for (Enumeration<InetAddress> enumIp = intf.getInetAddresses(); enumIp.hasMoreElements(); ) {
                    InetAddress addr = enumIp.nextElement();
                    if (!addr.isLoopbackAddress() && addr instanceof Inet4Address) {
                        list.add(addr.getHostAddress());
                    }
                }
            }
        } catch (Exception ignored) {}
        return list;
    }

    private boolean isPortOpen(String ip, int port, int timeout) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(ip, port), timeout);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void hideSystemUI() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
        );
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemUI();
        }
    }

    @Override
    public void onBackPressed() {
        if (remoteWebView.getVisibility() == View.VISIBLE) {
            exitSession();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        networkExecutor.shutdownNow();
    }
}

