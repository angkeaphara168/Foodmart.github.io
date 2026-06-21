(function () {
  var KEYS = {
    account: "foodmart_demo_account",
    cart: "foodmart_demo_cart",
    wishlist: "foodmart_demo_wishlist",
    orderStatus: "foodmart_demo_order_status",
    currentOrderId: "foodmart_demo_current_order",
    orderHistory: "foodmart_demo_order_history"
  };

  if (!/^https?:$/.test(window.location.protocol)) {
    return;
  }

  var original = {
    getItem: Storage.prototype.getItem,
    setItem: Storage.prototype.setItem,
    removeItem: Storage.prototype.removeItem
  };
  var syncKeys = {};
  var applyingRemoteState = false;

  Object.keys(KEYS).forEach(function (name) {
    syncKeys[KEYS[name]] = true;
  });

  function readJSON(key, fallback) {
    var value = original.getItem.call(localStorage, key);
    if (!value) return fallback;

    try {
      return JSON.parse(value);
    } catch (error) {
      return fallback;
    }
  }

  function readString(key, fallback) {
    var value = original.getItem.call(localStorage, key);
    return value === null ? fallback : value;
  }

  function currentSnapshot() {
    var orderStatus = readString(KEYS.orderStatus, null);
    var cart = readJSON(KEYS.cart, []);
    var wishlist = readJSON(KEYS.wishlist, []);
    var orderHistory = readJSON(KEYS.orderHistory, []);

    return {
      account: readJSON(KEYS.account, null),
      cart: Array.isArray(cart) ? cart : [],
      wishlist: Array.isArray(wishlist) ? wishlist : [],
      orderStatus: orderStatus === null || orderStatus === "" ? null : Number(orderStatus),
      currentOrderId: readString(KEYS.currentOrderId, null),
      orderHistory: Array.isArray(orderHistory) ? orderHistory : []
    };
  }

  function hasLocalData(snapshot) {
    return Boolean(
      snapshot.account ||
      snapshot.cart.length ||
      snapshot.wishlist.length ||
      snapshot.orderStatus !== null ||
      snapshot.currentOrderId ||
      snapshot.orderHistory.length
    );
  }

  function request(method, url, body) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open(method, url, false);
      xhr.setRequestHeader("Accept", "application/json");
      if (body) xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(body ? JSON.stringify(body) : null);
      if (xhr.status < 200 || xhr.status >= 300) return null;
      return JSON.parse(xhr.responseText || "{}");
    } catch (error) {
      return null;
    }
  }

  function writeLocal(key, value) {
    if (value === null || typeof value === "undefined") {
      original.removeItem.call(localStorage, key);
    } else {
      original.setItem.call(localStorage, key, value);
    }
  }

  function applyState(state) {
    applyingRemoteState = true;
    try {
      writeLocal(KEYS.account, state.account ? JSON.stringify(state.account) : null);
      writeLocal(KEYS.cart, JSON.stringify(Array.isArray(state.cart) ? state.cart : []));
      writeLocal(KEYS.wishlist, JSON.stringify(Array.isArray(state.wishlist) ? state.wishlist : []));
      writeLocal(KEYS.orderStatus, state.orderStatus === null || typeof state.orderStatus === "undefined" ? null : String(state.orderStatus));
      writeLocal(KEYS.currentOrderId, state.currentOrderId || null);
      writeLocal(KEYS.orderHistory, JSON.stringify(Array.isArray(state.orderHistory) ? state.orderHistory : []));
    } finally {
      applyingRemoteState = false;
    }
  }

  function syncToDatabase() {
    if (applyingRemoteState) return;
    request("POST", "/api/sync", currentSnapshot());
  }

  var remoteState = request("GET", "/api/state");
  if (remoteState) {
    if (remoteState.hasData) {
      applyState(remoteState);
    } else if (hasLocalData(currentSnapshot())) {
      syncToDatabase();
    }
  }

  Storage.prototype.setItem = function (key, value) {
    original.setItem.call(this, key, value);
    if (this === localStorage && syncKeys[key] && !applyingRemoteState) {
      syncToDatabase();
    }
  };

  Storage.prototype.removeItem = function (key) {
    original.removeItem.call(this, key);
    if (this === localStorage && syncKeys[key] && !applyingRemoteState) {
      syncToDatabase();
    }
  };
})();
