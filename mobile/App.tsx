import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'react-native';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { colors } from './src/theme/colors';

// Screens
import { DashboardScreen } from './src/screens/DashboardScreen';
import { AlertsScreen } from './src/screens/AlertsScreen';
import { ApprovalScreen } from './src/screens/ApprovalScreen';
import { PoliciesScreen } from './src/screens/PoliciesScreen';
import { ReportsScreen } from './src/screens/ReportsScreen';

// Tab Icons (simplified - in real app use react-native-vector-icons or expo-icons)
const TabIcon: React.FC<{ name: string; focused: boolean }> = ({ name, focused }) => {
  return (
    <View style={{
      width: 24,
      height: 24,
      backgroundColor: focused ? colors.primary.main : colors.light.text.tertiary,
      borderRadius: 12,
    }} />
  );
};

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

const TabNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: colors.primary.main,
        tabBarInactiveTintColor: colors.light.text.tertiary,
        tabBarStyle: {
          backgroundColor: colors.light.surface,
          borderTopColor: colors.light.border,
          paddingTop: 4,
          paddingBottom: 4,
        },
        headerStyle: {
          backgroundColor: colors.light.surface,
          borderBottomColor: colors.light.border,
        },
        headerTitleStyle: {
          fontWeight: '600',
          fontSize: 18,
        },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon name="dashboard" focused={focused} />,
          title: 'Dashboard',
        }}
      />
      <Tab.Screen
        name="Alerts"
        component={AlertsScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon name="alerts" focused={focused} />,
          title: 'Alerts',
          tabBarBadge: undefined, // Can be dynamically set based on unread count
        }}
      />
      <Tab.Screen
        name="Approve"
        component={ApprovalScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon name="approve" focused={focused} />,
          title: 'Approvals',
          tabBarBadge: undefined, // Can be dynamically set based on pending count
        }}
      />
      <Tab.Screen
        name="Policies"
        component={PoliciesScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon name="policies" focused={focused} />,
          title: 'Policies',
        }}
      />
      <Tab.Screen
        name="Reports"
        component={ReportsScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon name="reports" focused={focused} />,
          title: 'Reports',
        }}
      />
    </Tab.Navigator>
  );
};

const AppNavigator: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null; // Or a loading screen
  }

  if (!isAuthenticated) {
    // In a real app, show a login screen
    // For now, just show the main tabs
    return <TabNavigator />;
  }

  return (
    <Stack.Navigator>
      <Stack.Screen
        name="Main"
        component={TabNavigator}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <StatusBar barStyle="dark-content" backgroundColor={colors.light.background} />
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
};

export default App;
