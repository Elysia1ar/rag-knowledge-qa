import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
    const historyDrawerOpen = ref(false)

    function openHistory() {
        historyDrawerOpen.value = true
    }

    function closeHistory() {
        historyDrawerOpen.value = false
    }

    function toggleHistory() {
        historyDrawerOpen.value = !historyDrawerOpen.value
    }

    return { historyDrawerOpen, openHistory, closeHistory, toggleHistory }
})