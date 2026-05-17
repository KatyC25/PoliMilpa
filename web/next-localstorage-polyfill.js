// Small safe localStorage shim for Node 26+ (used in dev only)
(function () {
	try {
		// Node 26 has a native localStorage that warns without --localstorage-file.
		// Probe it once; if it throws, we shim.
		if (typeof globalThis.localStorage !== "undefined") {
			try {
				globalThis.localStorage.getItem("__probe__");
				return; // works fine, keep native
			} catch (_) {
				// native exists but is unusable — fall through to shim
			}
		}
	} catch (_) {}

	class LocalStorageShim {
		constructor() {
			this._data = new Map();
		}
		getItem(key) {
			const v = this._data.get(String(key));
			return v === undefined ? null : v;
		}
		setItem(key, value) {
			this._data.set(String(key), String(value));
		}
		removeItem(key) {
			this._data.delete(String(key));
		}
		clear() {
			this._data.clear();
		}
		key(n) {
			return Array.from(this._data.keys())[n] ?? null;
		}
		get length() {
			return this._data.size;
		}
	}

	try {
		// attach to global and globalThis
		const shim = new LocalStorageShim();
		Object.defineProperty(globalThis, "localStorage", {
			value: shim,
			writable: true,
			configurable: true,
			enumerable: false,
		});
		try {
			Object.defineProperty(global, "localStorage", {
				value: shim,
				writable: true,
				configurable: true,
				enumerable: false,
			});
		} catch (_) {}
	} catch (err) {
		// best-effort: if we cannot attach, ignore
	}
})();
