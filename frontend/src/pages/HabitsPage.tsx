// Habits page — list, create, edit, delete habits

import { useState } from "react";
import { useHabits, useCreateHabit, useDeleteHabit } from "@/hooks/useHabits";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import HabitCard from "@/components/habits/HabitCard";
import HabitForm from "@/components/habits/HabitForm";
import { Plus } from "lucide-react";
import type { HabitCreate } from "@/types/habit";

export default function HabitsPage() {
  const { data: habits, isLoading } = useHabits();
  const createHabit = useCreateHabit();
  const deleteHabit = useDeleteHabit();
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async (data: HabitCreate) => {
    await createHabit.mutateAsync(data);
    setShowForm(false);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Archive this habit? You can restore it later.")) {
      await deleteHabit.mutateAsync(id);
    }
  };

  if (isLoading) return <LoadingSpinner className="h-64" text="Loading habits..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">My Habits</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Habit
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h3 className="text-lg font-semibold mb-4">Create New Habit</h3>
          <HabitForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            isLoading={createHabit.isPending}
          />
        </div>
      )}

      {/* Habits Grid */}
      {habits && habits.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {habits.map((habit) => (
            <HabitCard key={habit.id} habit={habit} onDelete={handleDelete} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <span className="text-5xl">🎯</span>
          <h3 className="text-lg font-semibold mt-4">No habits yet</h3>
          <p className="text-gray-500 mt-2">
            Create your first habit to start tracking!
          </p>
        </div>
      )}
    </div>
  );
}
