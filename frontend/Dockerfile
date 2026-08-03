FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install && npm install sharp

COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
# These are injected at runtime by Cloud Run (not baked into the image)
ENV GOOGLE_CLIENT_ID=""
ENV GOOGLE_CLIENT_SECRET=""
ENV NEXTAUTH_SECRET=""
ENV NEXTAUTH_URL=""

RUN npm run build

EXPOSE 3000
ENV PORT=3000
CMD ["npm", "start"]
