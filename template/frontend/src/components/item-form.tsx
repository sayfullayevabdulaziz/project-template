import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

import { zItemCreate } from '@/client/zod.gen';
import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';

// Derived from the generated schema so the limits stay in sync; the form holds plain strings/booleans.
const schema = zItemCreate.extend({
  name: z.string().min(1, 'Name is required').max(200, 'Name must be at most 200 characters'),
  description: z.string().max(2000, 'Description must be at most 2000 characters'),
  is_published: z.boolean(),
});

export type ItemFormValues = z.infer<typeof schema>;

const EMPTY: ItemFormValues = { name: '', description: '', is_published: false };

type Props = {
  defaultValues?: ItemFormValues;
  onSubmit: (v: ItemFormValues) => Promise<void>;
  submitLabel: string;
};

export function ItemForm({ defaultValues = EMPTY, onSubmit, submitLabel }: Props) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormValues>({ resolver: zodResolver(schema), defaultValues });

  // Errors are surfaced by the caller (toast); swallow here so handleSubmit does not rethrow.
  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit(values);
    } catch {
      /* handled by the caller */
    }
  });

  return (
    <form onSubmit={(e) => void submit(e)} noValidate className="w-full max-w-xl">
      <FieldGroup>
        <Field data-invalid={!!errors.name}>
          <FieldLabel htmlFor="name">Name</FieldLabel>
          <Input id="name" aria-invalid={!!errors.name} {...register('name')} />
          <FieldError errors={[errors.name]} />
        </Field>
        <Field data-invalid={!!errors.description}>
          <FieldLabel htmlFor="description">Description</FieldLabel>
          <textarea
            id="description"
            rows={4}
            aria-invalid={!!errors.description}
            className="min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive"
            {...register('description')}
          />
          <FieldError errors={[errors.description]} />
        </Field>
        <Field orientation="horizontal">
          <Controller
            control={control}
            name="is_published"
            render={({ field }) => (
              <Switch id="is_published" checked={field.value} onCheckedChange={field.onChange} />
            )}
          />
          <FieldLabel htmlFor="is_published">Published</FieldLabel>
        </Field>
        <Button type="submit" disabled={isSubmitting}>
          {submitLabel}
        </Button>
      </FieldGroup>
    </form>
  );
}
