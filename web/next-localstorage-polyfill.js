// Small safe localStorage shim for Node (used in dev only)
(function () {
	try {
		if (
			typeof globalThis.localStorage !== "undefined" &&
			typeof globalThis.localStorage.getItem === "function"
		) {
			return; // already proper
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
