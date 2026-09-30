// ============================================================================
// useHabits — TanStack Query hooks for habit CRUD
// ============================================================================
// WHY TANSTACK QUERY (not useEffect + useState):
//   - Auto caching: doesn't refetch if data is fresh
//   - Auto refetch on window focus (data stays current)
//   - Loading/error states built-in (no manual isLoading tracking)
//   - Optimistic updates for mutations (UI updates before API responds)
//   - Automatic retry on failure
//
//   Without TanStack Query, every component that shows habits needs:
//     const [habits, setHabits] = useState([]);
//     const [loading, setLoading] = useState(true);
//     const [error, setError] = useState(null);
//     useEffect(() => { fetchHabits()... }, []);
//   That's 10 lines of boilerplate per component. TanStack Query: 1 line.
// ============================================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { habitService } from "@/services/habit.service";
import type { HabitCreate, HabitUpdate } from "@/types/habit";

// Query key constants — used for cache invalidation
const HABITS_KEY = ["habits"];

export function useHabits(includeArchived = false) {
  return useQuery({
    queryKey: [...HABITS_KEY, { includeArchived }],
    queryFn: () => habitService.getHabits(includeArchived),
  });
}

export function useHabit(id: string) {
  return useQuery({
    queryKey: [...HABITS_KEY, id],
    queryFn: () => habitService.getHabit(id),
    enabled: !!id, // Don't fetch if id is empty
  });
}

export function useCreateHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: HabitCreate) => habitService.createHabit(data),
    onSuccess: () => {
      // Invalidate habits cache — triggers refetch of the habit list
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useUpdateHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: HabitUpdate }) =>
      habitService.updateHabit(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useDeleteHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => habitService.deleteHabit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useReorderHabits() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (habitIds: string[]) =>
      habitService.reorderHabits({ habit_ids: habitIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}
