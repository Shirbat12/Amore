// Shared guard for content scripts. After Reload in chrome://extensions, open tabs
// keep an old script that must stop calling chrome.* APIs.
(function () {
  let retired = false;
  const retireCallbacks = [];

  function retire() {
    if (retired) return;
    retired = true;
    for (let i = 0; i < retireCallbacks.length; i++) {
      retireCallbacks[i]();
    }
  }

  function isInvalidatedError(err) {
    const msg = String((err && err.message) || err || "");
    return msg.indexOf("Extension context invalidated") !== -1;
  }

  window.__amoreOnRetire = function (fn) {
    if (retired) {
      fn();
      return;
    }
    retireCallbacks.push(fn);
  };

  window.__amoreExtensionAlive = function () {
    if (retired) return false;
    try {
      if (!chrome.runtime || !chrome.runtime.id) {
        retire();
        return false;
      }
      return true;
    } catch (e) {
      retire();
      return false;
    }
  };

  window.__amoreStorageGet = async function (keys) {
    if (!window.__amoreExtensionAlive()) return {};
    try {
      return await chrome.storage.local.get(keys);
    } catch (e) {
      if (isInvalidatedError(e)) retire();
      return {};
    }
  };

  window.__amoreSendMessage = function (msg, callback) {
    if (!window.__amoreExtensionAlive()) return;
    try {
      chrome.runtime.sendMessage(msg, (result) => {
        if (chrome.runtime.lastError) {
          if (isInvalidatedError(chrome.runtime.lastError.message)) retire();
          return;
        }
        if (callback) callback(result);
      });
    } catch (e) {
      if (isInvalidatedError(e)) retire();
    }
  };

  window.__amoreStorageListen = function (listener) {
    if (!window.__amoreExtensionAlive()) return;
    try {
      chrome.storage.onChanged.addListener(function (changes, area) {
        if (!window.__amoreExtensionAlive()) return;
        listener(changes, area);
      });
    } catch (e) {
      if (isInvalidatedError(e)) retire();
    }
  };
})();
