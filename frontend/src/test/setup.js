const storage = new Map()

const localStorageMock = {
  get length() {
    return storage.size
  },
  clear() {
    storage.clear()
  },
  getItem(key) {
    const value = storage.get(String(key))
    return value === undefined ? null : value
  },
  key(index) {
    return Array.from(storage.keys())[index] || null
  },
  removeItem(key) {
    storage.delete(String(key))
  },
  setItem(key, value) {
    storage.set(String(key), String(value))
  },
}

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: localStorageMock,
})

Object.defineProperty(window, 'localStorage', {
  configurable: true,
  value: localStorageMock,
})
