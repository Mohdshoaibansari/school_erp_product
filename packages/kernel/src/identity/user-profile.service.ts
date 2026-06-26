import { PrismaClient, UserProfile, Prisma } from '@school-erp/database';

export interface CreateProfileInput {
  firstName: string;
  lastName: string;
  phone?: string;
  avatar?: string;
  dateOfBirth?: Date;
  gender?: 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY';
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
}

export interface UpdateProfileInput {
  firstName?: string;
  lastName?: string;
  phone?: string;
  avatar?: string;
  dateOfBirth?: Date;
  gender?: 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY';
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
}

export class UserProfileService {
  constructor(private prisma: PrismaClient) {}

  async getByUserId(userId: string): Promise<UserProfile | null> {
    return this.prisma.userProfile.findFirst({
      where: { userId, deletedAt: null },
    });
  }

  async create(userId: string, data: CreateProfileInput): Promise<UserProfile> {
    const existing = await this.prisma.userProfile.findFirst({
      where: { userId, deletedAt: null },
    });
    if (existing) {
      throw new Error('Profile already exists for this user');
    }

    return this.prisma.userProfile.create({
      data: {
        userId,
        ...data,
      },
    });
  }

  async update(userId: string, data: UpdateProfileInput): Promise<UserProfile> {
    const existing = await this.prisma.userProfile.findFirst({
      where: { userId, deletedAt: null },
    });
    if (!existing) {
      throw new Error('Profile not found for this user');
    }

    return this.prisma.userProfile.update({
      where: { userId },
      data,
    });
  }

  async upsert(userId: string, data: CreateProfileInput): Promise<UserProfile> {
    return this.prisma.userProfile.upsert({
      where: { userId },
      update: data,
      create: {
        userId,
        ...data,
      },
    });
  }

  async archive(userId: string): Promise<UserProfile> {
    const existing = await this.prisma.userProfile.findFirst({
      where: { userId, deletedAt: null },
    });
    if (!existing) {
      throw new Error('Profile not found for this user');
    }

    return this.prisma.userProfile.update({
      where: { userId },
      data: { deletedAt: new Date() },
    });
  }
}
