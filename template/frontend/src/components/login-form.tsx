import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import type { LoginRequest } from '@/client';
import { zLoginRequest } from '@/client/zod.gen';
import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { getProblem } from '@/lib/problem';

export function LoginForm({ onSubmit }: { onSubmit: (v: LoginRequest) => Promise<void> }) {
  const [serverError, setServerError] = useState<string>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginRequest>({ resolver: zodResolver(zLoginRequest) });

  const submit = handleSubmit(async (values) => {
    setServerError(undefined);
    try {
      await onSubmit(values);
    } catch (err) {
      const p = getProblem(err);
      setServerError(p.detail ?? p.title);
    }
  });

  return (
    <form onSubmit={(e) => void submit(e)} noValidate className="w-full max-w-sm">
      <FieldGroup>
        <Field data-invalid={!!errors.email}>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input id="email" type="email" autoComplete="username" {...register('email')} />
          <FieldError errors={[errors.email]} />
        </Field>
        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...register('password')}
          />
          <FieldError errors={[errors.password]} />
        </Field>
        <FieldError>{serverError}</FieldError>
        <Button type="submit" disabled={isSubmitting}>
          Sign in
        </Button>
      </FieldGroup>
    </form>
  );
}
