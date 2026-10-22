import { Link } from '@tanstack/react-router';

import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/items', label: 'Items' },
  { to: '/users', label: 'Users' },
] as const;

export function AppSidebar({ email, onLogout }: { email: string; onLogout: () => void }) {
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {links.map(({ to, label }) => (
                <SidebarMenuItem key={to}>
                  <SidebarMenuButton asChild>
                    <Link to={to} activeOptions={{ exact: to === '/' }}>
                      {label}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <p className="truncate px-2 text-sm text-muted-foreground">{email}</p>
        <Button variant="outline" onClick={onLogout}>
          Log out
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
