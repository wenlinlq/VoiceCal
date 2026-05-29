import { defineStore } from 'pinia'
import { formatDate } from '@/utils/date.js'

/** @type {import('@/types/definitions.js').Event[]} */
const MOCK_EVENTS = [
  {
    id: 1,
    title: '产品评审会',
    start_time: '2026-05-29 15:00:00',
    end_time: '2026-05-29 16:00:00',
    repeat_type: 'none',
    note: '腾讯会议 123456'
  },
  {
    id: 2,
    title: '周报提交',
    start_time: '2026-05-29 17:00:00',
    end_time: '2026-05-29 17:30:00',
    repeat_type: 'weekly',
    note: ''
  },
  {
    id: 3,
    title: '健身',
    start_time: '2026-05-29 19:00:00',
    end_time: '2026-05-29 20:00:00',
    repeat_type: 'none',
    note: '健身房 3楼'
  },
  {
    id: 4,
    title: '团队周会',
    start_time: '2026-05-30 10:00:00',
    end_time: '2026-05-30 11:00:00',
    repeat_type: 'weekly',
    note: ''
  },
  {
    id: 5,
    title: '客户拜访',
    start_time: '2026-06-02 14:00:00',
    end_time: '2026-06-02 16:00:00',
    repeat_type: 'none',
    note: '地址：科技园A座'
  },
  {
    id: 6,
    title: '项目讨论',
    start_time: '2026-05-15 14:00:00',
    end_time: '2026-05-15 15:00:00',
    repeat_type: 'none',
    note: ''
  }
]

export const useCalendarStore = defineStore('calendar', {
  state: () => ({
    events: [...MOCK_EVENTS],
    currentDate: formatDate(new Date()),
    viewYear: new Date().getFullYear(),
    viewMonth: new Date().getMonth()
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
    }
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
      return this.events.find((e) => e.id === Number(id))
    },

    async fetchEvents(date) {
      // 静态阶段：直接返回本地数据
      if (date) this.currentDate = date
      return this.events
    },

    async addEvent(event) {
      const newEvent = {
        id: Date.now(),
        ...event
      }
      this.events.push(newEvent)
      return newEvent
    },

    async deleteEvent(id) {
      this.events = this.events.filter((e) => e.id !== id)
    },

    async updateEvent(event) {
      const index = this.events.findIndex((e) => e.id === event.id)
      if (index !== -1) {
        this.events[index] = { ...this.events[index], ...event }
      }
    }
  }
})
