import { PrismaClient, Conversation, Message } from '@school-erp/database';

export interface SendMessageInput {
  conversationId: string;
  senderId: string;
  content: string;
}

export interface CreateConversationInput {
  tenantId: string;
  institutionId: string;
  participantIds: string[];
}

export class CommunicationService {
  constructor(private prisma: PrismaClient) {}

  async createConversation(input: CreateConversationInput): Promise<Conversation> {
    const { tenantId, institutionId, participantIds } = input;

    if (participantIds.length < 2) {
      throw new Error('Conversation must have at least 2 participants');
    }

    // Check if conversation already exists between these participants
    const existing = await this.prisma.conversation.findFirst({
      where: {
        tenantId,
        institutionId,
        participants: {
          every: {
            userId: { in: participantIds },
          },
        },
      },
      include: {
        participants: true,
      },
    });

    if (existing && existing.participants.length === participantIds.length) {
      return existing;
    }

    return this.prisma.conversation.create({
      data: {
        tenantId,
        institutionId,
        participants: {
          create: participantIds.map((userId) => ({ userId })),
        },
      },
      include: {
        participants: true,
      },
    });
  }

  async sendMessage(input: SendMessageInput): Promise<Message> {
    const { conversationId, senderId, content } = input;

    // Verify conversation exists and sender is a participant
    const conversation = await this.prisma.conversation.findFirst({
      where: {
        id: conversationId,
        participants: {
          some: {
            userId: senderId,
          },
        },
      },
    });

    if (!conversation) {
      throw new Error('Conversation not found or user is not a participant');
    }

    return this.prisma.message.create({
      data: {
        conversationId,
        senderId,
        content,
      },
    });
  }

  async getConversation(conversationId: string): Promise<Conversation | null> {
    return this.prisma.conversation.findUnique({
      where: { id: conversationId },
      include: {
        participants: true,
        messages: {
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
    });
  }

  async getConversations(
    tenantId: string,
    userId: string,
    options: { skip?: number; take?: number } = {}
  ): Promise<Conversation[]> {
    const { skip = 0, take = 50 } = options;

    return this.prisma.conversation.findMany({
      where: {
        tenantId,
        participants: {
          some: {
            userId,
          },
        },
      },
      include: {
        participants: true,
        messages: {
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
      skip,
      take,
      orderBy: { updatedAt: 'desc' },
    });
  }

  async getMessages(
    conversationId: string,
    options: { skip?: number; take?: number } = {}
  ): Promise<Message[]> {
    const { skip = 0, take = 50 } = options;

    return this.prisma.message.findMany({
      where: { conversationId },
      skip,
      take,
      orderBy: { createdAt: 'asc' },
    });
  }

  async getUnreadCount(tenantId: string, userId: string): Promise<number> {
    // For simplicity, count messages in conversations where user is a participant
    // but hasn't sent the last message
    const conversations = await this.prisma.conversation.findMany({
      where: {
        tenantId,
        participants: {
          some: { userId },
        },
      },
      include: {
        messages: {
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
    });

    let unreadCount = 0;
    for (const conv of conversations) {
      if (conv.messages.length > 0 && conv.messages[0].senderId !== userId) {
        unreadCount++;
      }
    }

    return unreadCount;
  }
}
