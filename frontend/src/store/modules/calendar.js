import { defineStore } from 'pinia'
import { formatDate } from '@/utils/date.js'
import * as eventsApi from '@/api/events.js'
import { normalizeEvent, toApiEventPayload } from '@/utils/event-mapper.js'

export const useCalendarStore = defineStore('calendar', {
  state: () => ({
    events: [],
    loading: false,
    loaded: false,
    error: '',
    currentDate: formatDate(new Date()),
    viewYear: new Date().getFullYear(),
    viewMonth: new Date().getMonth(),
  }),

  getters: {
    todayEvents(state) {
      return state.events
        .filter((e) => e.start_time.startsWith(state.currentDate))
        .sort((a, b) => a.start_time.localeCompare(b.start_time))
    },

    eventDates(state) {
      const dates = new Set()
      state.events.forEach((e) => {
        dates.add(e.start_time.slice(0, 10))
      })
      return dates
    },

    hasEventsOnDate: (state) => (dateStr) => {
      return state.events.some((e) => e.start_time.startsWith(dateStr))
    },
  },

  actions: {
    setCurrentDate(date) {
      this.currentDate = date
    },

    setViewMonth(year, month) {
      this.viewYear = year
      this.viewMonth = month
    },

    getEventById(id) {
      return this.events.find((e) => String(e.id) === String(id))
    },

    async fetchEvents(date) {
      if (date) this.currentDate = date
      this.loading = true
      this.error = ''

      try {
        const list = await eventsApi.listEvents()
        this.events = (list || []).map(normalizeEvent)
        this.loaded = true
        return this.events
      } catch (err) {
        this.error = err.message || '加载日程失败'
        console.error('[calendar] fetchEvents failed', err)
        throw err
      } finally {
        this.loading = false
      }
    },

    /** 语音 Agent 一轮 turn.done 后刷新日程列表 */
    async syncAfterVoiceTurn() {
      return this.fetchEvents(this.currentDate)
    },

    async fetchEventById(id) {
      const cached = this.getEventById(id)
      if (cached) return cached

      try {
        const raw = await eventsApi.getEvent(id)
        const event = normalizeEvent(raw)
        const index = this.events.findIndex((e) => String(e.id) === String(id))
        if (index === -1) {
          this.events.push(event)
        } else {
          this.events[index] = event
        }
        return event
      } catch (err) {
        console.error('[calendar] fetchEventById failed', err)
        throw err
      }
    },

    async addEvent(event) {
      const payload = toApiEventPayload(event)
      const raw = await eventsApi.createEvent(payload)
      const newEvent = normalizeEvent(raw)
      this.events.push(newEvent)
      return newEvent
    },

    async deleteEvent(id) {
      await eventsApi.deleteEvent(id)
      this.events = this.events.filter((e) => String(e.id) !== String(id))
    },

    async toggleEventComplete(id) {
      const event = this.events.find((e) => String(e.id) === String(id))
      if (event) {
        event.completed = !event.completed
      }
    },

    async updateEvent(event) {
      const payload = toApiEventPayload(event)
      const raw = await eventsApi.updateEvent(event.id, payload)
      const updated = normalizeEvent(raw)
      const index = this.events.findIndex((e) => String(e.id) === String(event.id))
      if (index !== -1) {
        this.events[index] = {
          ...updated,
          repeat_type: event.repeat_type ?? this.events[index].repeat_type,
          completed: event.completed ?? this.events[index].completed,
        }
      }
      return this.events[index]
    },
  },
})
