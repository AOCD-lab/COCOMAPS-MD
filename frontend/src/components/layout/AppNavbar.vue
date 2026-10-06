<template>
  <nav class="nav-bar">
    <div class="nav-left">
      <router-link to="/" class="nav-logo">
        <img :src="logoUrl" alt="COCOMAPS-MD" class="nav-logo-img" />
      </router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link" exact>Home</router-link>
        <router-link to="/jobs" class="nav-link">Jobs</router-link>
        <router-link to="/about" class="nav-link">About</router-link>
        <router-link to="/help" class="nav-link">Help</router-link>
        <router-link to="/examples" class="nav-link">Examples</router-link>
        <router-link to="/references" class="nav-link">References</router-link>
      </div>
    </div>
    <div class="nav-right">
      <slot name="right" />
    </div>
  </nav>
</template>

<script setup>
// Reference public assets via the configured base path so the logo resolves
// under /BioTools/COCOMAPS-MD/ (a root-absolute /images/... 404s behind the proxy).
const logoUrl = import.meta.env.BASE_URL + 'images/cocomaps.png'
</script>

<style scoped>
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  text-decoration: none;
}

.nav-logo-img {
  display: block;
  height: 29px;
  width: auto;
}

.nav-links {
  display: flex;
  gap: 32px;
  margin-left: 32px;
}

.nav-link {
  font-size: 15px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  transition: color 0.15s ease;
  position: relative;
  padding-bottom: 4px;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: #1d1d1f;
  transition: width 0.15s ease;
}

.nav-link:hover,
.nav-link.router-link-active,
.nav-link.router-link-exact-active {
  color: #1d1d1f;
}

.nav-link.router-link-active::after,
.nav-link.router-link-exact-active::after {
  width: 100%;
}

@media (max-width: 768px) {
  .nav-bar {
    padding: 16px 24px;
  }

  .nav-links {
    gap: 20px;
  }
}
</style>
